from storage import Storage
from openai import OpenAI
import streamlit as st
from activities_parsing import extract_activity_summary, format_activity_for_prompt
# Initialize the OpenAI client
openai_api_key = st.secrets["openai_api_key"]
client = OpenAI(api_key=openai_api_key)  # or use environment variable

instructions_coaching = '''
                        You are an elite trail running coach and sport scientist.

                        You will receive detailed activity data from a single run (distance, pace, splits, elevation, HR, cadence, etc.). Based on this, provide structured feedback organized by the following categories.

                        You will also receive the user's past activities and goals. Adjust your feedback based on it.

                        Respond using **Markdown formatting** with clear section headers. Make very short and precise feedback, do not make real sentences

                        ###GUIDELINES###
                        Provide a recommandation only at the end for the last category 'Progression'. Do not send a recommandation for every field


                        1. **Analysis** (brief comparison to previous efforts and relevance to goal)
                        2. **2 concise recommendations** (next workouts or adjustments)
                        3. **Warnings or advice if relevant** (e.g., signs of fatigue, overtraining)
                        4. **Progression** (what does this workout tell us about current fitness? what can the athlete improve on in future sessions?)
                        Keep it short and valuable. Avoid generic motivation or repetition of data.

                        Use a **supportive and coaching tone**. Be specific and actionable.
                    '''

def generate_content(input_text: str, athlete_id: str, prompt:str, activity_id:str,model="gpt-4o", temperature=1.0) -> str:
    # Deduct one credit from the user's account
    storage = Storage()
    user_data = storage.get_user_data(athlete_id)
    athletes_info = user_data.get('athletes_info', {})
    credits = athletes_info.get('credits', 0)
    used_credits = athletes_info.get('used_credits', 0)
    last_activities = storage.get_user_activities(athlete_id)

    full_past_act = ""
    for activity in last_activities[:10]:
        summary = extract_activity_summary(activity)
        str_summary = format_activity_for_prompt(summary)
        full_past_act += str_summary + "\n\n"
    print(full_past_act)
    user_goal = f'''
                ###USER PREVIOUS ACTIVITIES###
                Based on the previous activities, provide the user pertinents informations about his progression
                {last_activities}

                ###USER GOAL: find bellow the objective of the user
                Distance is in kilometers and elevation is in meters
                {prompt}

                '''
    user_goal = user_goal + instructions_coaching

    if user_data and credits > 0:
        storage.update_user_credits(athlete_id=athlete_id, credits=credits - 1, used_credits=used_credits +1)
    else:
        raise ValueError("Insufficient credits to generate content.")
    print(user_goal)
    response = client.responses.create(
        model=model,
        temperature=temperature,
        instructions=user_goal,
        input=input_text
    )

    storage.update_activity_coach(athlete_id=athlete_id, activity_id=activity_id, coach_feedback=response.output_text)
    print(len(response.output_text))
    return response.output_text




instructions_running = '''
                        You are an elite trail running coach and sport scientist.

                        You will receive detailed activity data from a single run (distance, pace, splits, elevation, HR, cadence, etc.). Based on this, provide structured feedback organized by the following categories.

                        Respond using **Markdown formatting** with clear section headers. Make very short and precise feedback, do not make real sentences

                        ###GUIDELINES###
                        Provide a recommandation only at the end for the last category 'Progression'. Do not send a recommandation for every field


                        🏃 Pacing
                        - Was pacing consistent across splits?
                        - Was there a strong or weak finish?

                        ❤️ HeartRate & Intensity
                        - Was the effort aerobic or anaerobic?

                        ⚙️ Cadence & Biomechanics
                        - Was cadence efficient (around 170–180 spm)?

                        ⛰️ Hill Handling
                        - How did the athlete handle elevation gain?

                        🔁 Splits & Segments
                        - Highlight any strong or weak splits.

                        🔄 Recovery
                        - Based on intensity and suffer score, suggest recovery time.
                        - Recommend type of next session (recovery, endurance, intervals, etc.)

                        📈 Progression
                        - What does this workout tell us about current fitness?
                        - What can the athlete improve on in future sessions?

                        Use a **supportive and coaching tone**. Be specific and actionable.
                    '''
