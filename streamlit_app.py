import streamlit as st
import requests
import urllib.parse
import time
from activities_parsing import extract_activity_summary,format_activity_for_prompt, update_activity_by_id,post_activity_comment, generate_user_identifier
from strava_api import get_token, get_athlete_details, get_athlete_stats, get_activities, get_valid_token,get_strava_auth_url, get_activity_details,remove_character
from llm import generate_content
from storage import Storage
import pandas as pd
import altair as alt

st.set_page_config(
   page_title="WildStride - AI Coach",
   page_icon="🏃",
   layout="wide",
   initial_sidebar_state="expanded",
)

# Initialize storage
storage = Storage()

# Replace with your own Strava API credentials
# CLIENT_ID = st.secrets["strava_client_id"]
# CLIENT_SECRET = st.secrets["strava_client_secret"]

# Initialize session state for athlete_id and access_token if not exists
if 'athlete_id' not in st.session_state:
    st.session_state.athlete_id = None
if 'access_token' not in st.session_state:
    st.session_state.access_token = None
if 'athlete_updated' not in st.session_state:
    st.session_state.athlete_updated = False

# Initialize session state for credits, used_credits, and is_coached if not exists
if 'credits' not in st.session_state:
    st.session_state.credits = 0
if 'used_credits' not in st.session_state:
    st.session_state.used_credits = 0
if 'is_coached' not in st.session_state:
    st.session_state.is_coached = {}


query_params = st.query_params
code = query_params.get("code", None)

if code :
    if st.button("💡 How to use WildStride?"):
        st.write("WildStride is a platform that uses AI to help you become a better runner. It uses your Strava data to provide you with personalized coaching advice.")
        st.write("To use WildStride, you need to connect your Strava account to the app.")
        st.write("Once you have connected your Strava account, you can start using the app to get personalized coaching advice.")
        st.write("The app will use your Strava data to provide you with personalized coaching advice.")
        st.write("To receive a coaching advice, you need to have enough credits.")
        st.write("You can gain credits by recommending the app to a friend.")
        st.write("You can also gain credits by completing the onboarding process.")


if code:
    # Initial token exchange
    token_data = get_token(code)
    access_token = token_data.get("access_token")
    athlete_id = str(token_data.get("athlete", {}).get("id"))


    if (access_token and athlete_id)  or (st.session_state.athlete_id is not None and st.session_state.access_token is not None):
        # Store tokens
        storage.save_strava_tokens(athlete_id, token_data)
        st.session_state.athlete_id = athlete_id
        st.session_state.access_token = access_token
        st.success("✅ Logged in to Strava!")

        # Get athlete details and stats
        athlete = get_athlete_details(access_token)
        athlete_stats = get_athlete_stats(access_token, athlete_id)

        # Update athlete data only if not already updated
        if not st.session_state.athlete_updated:
            storage.update_athlete(athlete)
            storage.update_athlete_stats(athlete_id, athlete_stats)
            st.session_state.athlete_updated = True

        # Display athlete profile
        col1, col2 = st.columns([1, 3])
        with col1:
            if athlete.get('profile'):
                st.image(athlete['profile'], width=300)
        with col2:
            st.subheader(f"👋 Welcome, {athlete.get('firstname', '')} {athlete.get('lastname', '')}")
            st.write(f"📍 {athlete.get('city', '')}, {athlete.get('country', '')}")

            # Display athlete stats
        if athlete_stats:
            # Year-to-date Stats
            st.subheader("📊 Your Year-to-Date Stats:")
            ytd_stats = storage.get_athlete_stats(athlete_id).get('ytd', {})

            # Running stats
            if 'run' in ytd_stats:
                st.write("🏃‍♂️ Running:")
                run_stats = ytd_stats['run']
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Activities", f"{run_stats['total_activities']}",  border=True)
                with col2:
                    st.metric("Distance", f"{run_stats['total_distance']/1000:.1f} km",  border=True)
                with col3:
                    st.metric("Elevation", f"{run_stats['total_elevation']:.0f} m",  border=True)

            # Cycling stats
            if 'ride' in ytd_stats:
                st.write("🚴‍♂️ Cycling:")
                ride_stats = ytd_stats['ride']
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Activities", f"{ride_stats['total_activities']}",  border=True)
                with col2:
                    st.metric("Distance", f"{ride_stats['total_distance']/1000:.1f} km",  border=True)
                with col3:
                    st.metric("Elevation", f"{ride_stats['total_elevation']:.0f} m",  border=True)

            # All-time Stats in an expander
            st.subheader("📈 View All-Time Stats")
            all_time_stats = storage.get_athlete_stats(athlete_id).get('all_time', {})

                # Running all-time stats
            if 'run' in all_time_stats:
                st.write("🏃‍♂️ Running:")
                run_stats = all_time_stats['run']
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Activities", f"{run_stats['total_activities']}",  border=True)
                with col2:
                    st.metric("Distance", f"{run_stats['total_distance']/1000:.1f} km",  border=True)
                with col3:
                    st.metric("Elevation", f"{run_stats['total_elevation']:.0f} m",  border=True)

            # Cycling all-time stats
            if 'ride' in all_time_stats:
                st.write("🚴‍♂️ Cycling:")
                ride_stats = all_time_stats['ride']
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Activities", f"{ride_stats['total_activities']}",  border=True)
                with col2:
                    st.metric("Distance", f"{ride_stats['total_distance']/1000:.1f} km",  border=True)
                with col3:
                    st.metric("Elevation", f"{ride_stats['total_elevation']:.0f} m",  border=True)

        # Get or initialize user data
        user_data = storage.get_user_data(athlete_id) or {}
        preferences = user_data.get('preferences', {})
        athletes_info = user_data.get('athletes_info', {})

        # Display available credits in the sidebar
        credits = athletes_info.get('credits', 3)
        used_credits = athletes_info.get('used_credits', 0)

        #define state
        st.session_state.credits = credits
        st.session_state.used_credits = used_credits

        sidebar_img = "https://i.imgur.com/dUXI1Tp.jpeg"
        st.sidebar.image(sidebar_img, use_container_width=True)
        st.sidebar.subheader("💳 Available Credits")
        def_color = "green" if credits > 0 else "red"
        st.sidebar.write(f":{def_color}-background[You have {st.session_state.credits} credits available.]")
        st.sidebar.write(f":blue-background[You have used {st.session_state.used_credits} credits so far!]")

        # Add message about gaining new credits
        st.sidebar.info("To gain new credits and to progress with AI coach, contact us at contact.wildstride@gmail.com or recommend the app to a friend to get free credits.")
        print(f"athlete infos >>> : {athletes_info}")
        used_ref_code = athletes_info.get('used_ref_code', 'empty')

        if used_ref_code == 'empty':
            ref_code_input = st.sidebar.text_input('Type a friend referral code')
            if 'ref_code_submitted' not in st.session_state:
                st.session_state.ref_code_submitted = False
            if not st.session_state.ref_code_submitted:
                if st.sidebar.button('Submit Code'):
                    if ref_code_input:
                        storage.update_athlete_used_ref_code(athlete_id=athlete_id, used_ref_code=ref_code_input)
                        st.session_state.ref_code_submitted = True
                        st.sidebar.success('Referral code submitted successfully!')
                        st.sidebar.write(f':green-background[Referral Code Used: {ref_code_input}]')
        else:
            st.sidebar.write(f':green-background[Referral Code Used: {used_ref_code}]')

        st.sidebar.write(f":green-background[Your referral code is :  {generate_user_identifier(athlete.get('firstname'), athlete.get('lastname'), athlete.get('id'))}]", border=True)
        # Ensure token is valid before updating goals
        access_token, athlete_id = get_valid_token(athlete_id)

        if access_token and athlete_id:
    # Query user preferences from the database
            user_data = storage.get_user_data(athlete_id) or {}
            if preferences not in st.session_state:
                 st.session_state.preferences = user_data.get('preferences', {})

            # User preferences section in the sidebar

            if 'sport_type' not in st.session_state:
                st.session_state.sport_type = preferences.get('sport_type', 'Run')
            if 'target_distance' not in st.session_state:
                st.session_state.target_distance = preferences.get('target_distance', 100)
            if 'target_elevation' not in st.session_state:
                st.session_state.target_elevation = preferences.get('target_elevation', 50)
            if 'hours' not in st.session_state:
                st.session_state.hours = preferences.get('target_time_hours', 1)
            if 'minutes' not in st.session_state:
                st.session_state.minutes = preferences.get('target_time_minutes', 0)
            if 'seconds' not in st.session_state:
                st.session_state.seconds = preferences.get('target_time_seconds', 0)
            if 'target_date' not in st.session_state:
                st.session_state.target_date = preferences.get('target_date', None)

            # User preferences section in the sidebar
            st.sidebar.subheader("🎯 Your Training Goals")

            goal_wording = ""
            if(len(st.session_state.preferences) == 0):
                goal_wording = "Set my goal!"
                st.sidebar.subheader("Set your objective below!")
                st.sidebar.subheader("Our AI coach will help you achieve your goals.")
            else :
                st.sidebar.subheader("✅ Your objective is setted")
                goal_wording = "Update my goal!"
            # Allow user to choose sport type
            st.session_state.sport_type = st.sidebar.selectbox(
                "Select Sport Type",
                ["Run", "Trail", "Bike"],
                index=["Run", "Trail", "Bike"].index(st.session_state.sport_type)
            )

            # Allow user to set new goals
            st.session_state.target_distance = st.sidebar.number_input(
                "Target Race Distance (km)",
                value=st.session_state.target_distance,
                min_value=1
            )
            st.session_state.target_elevation = st.sidebar.number_input(
                "Target Race Elevation (m)",
                value=st.session_state.target_elevation,
                min_value=0
            )

            # Add target time inputs
            col1, col2, col3 = st.sidebar.columns(3)
            with col1:
                st.session_state.hours = st.number_input(
                    "Hours",
                    value=st.session_state.hours,
                    min_value=0,
                    max_value=24
                )
            with col2:
                st.session_state.minutes = st.number_input(
                    "Minutes",
                    value=st.session_state.minutes,
                    min_value=0,
                    max_value=59
                )
            with col3:
                st.session_state.seconds = st.number_input(
                    "Seconds",
                    value=st.session_state.seconds,
                    min_value=0,
                    max_value=59
                )

            # Calculate target pace
            if st.session_state.target_distance > 0:
                equivalent_distance_from_elevation = st.session_state.target_elevation / 100.0

                # Adjust total distance
                adjusted_distance = st.session_state.target_distance + equivalent_distance_from_elevation

                total_seconds = (st.session_state.hours * 3600) + (st.session_state.minutes * 60) + st.session_state.seconds
                pace_seconds_per_km = total_seconds / adjusted_distance
                pace_minutes = int(pace_seconds_per_km // 60)
                pace_seconds = int(pace_seconds_per_km % 60)

            st.session_state.target_date = st.sidebar.date_input(
                "Target Race Date",
                value=st.session_state.target_date
            )

            if st.sidebar.button(goal_wording):
                with st.spinner("Loading..."):
                    time.sleep(2)
                storage.update_user_preferences(athlete_id, {
                    'sport_type': st.session_state.sport_type,
                    'target_distance': st.session_state.target_distance,
                    'target_elevation': st.session_state.target_elevation,
                    'target_date': st.session_state.target_date.isoformat() if st.session_state.target_date else None,
                    'target_time_hours': st.session_state.hours,
                    'target_time_minutes': st.session_state.minutes,
                    'target_time_seconds': st.session_state.seconds
                })
                st.sidebar.success("✅ Goals saved!")
        else:
            st.error("❌ Failed to retrieve access token 1.")

        if credits > 0 :
            st.subheader(f"You have {credits} credits left!")

            if(len(st.session_state.preferences) == 0):
                st.subheader(f"Set your goals first to receive your coaching advice")
            else :
                st.subheader(f"Coaching available for the following activities")

        # Show activity history
        st.subheader("📊 Activity History")
        activities = get_activities(access_token)
        history_activities = storage.get_user_activities(athlete_id)

        stored_activity_ids = {activity['activity_id'] for activity in history_activities}

# Iterate over retrieved activities
        for activity in activities:
            activity_id = str(activity['id'])  # Ensure activity_id is a string
            if activity_id not in stored_activity_ids:
                # New activity, add to the database
                summary = extract_activity_summary(activity)
                str_summary = format_activity_for_prompt(summary)
                storage.add_activity(athlete_id, activity, str_summary)
            else:
                # Existing activity, update if necessary
                # You can add logic here to update the activity if needed
                pass
        history = storage.get_user_activities(athlete_id)
        if  history:
            # Convert history to a DataFrame for easier manipulation
            df = pd.DataFrame(history)

            # Display activities in columns
            cols = st.columns(4, border=True)
            for index, past_activity in enumerate(history):
                with cols[index % 4]:
                    activity_type = past_activity.get('sport_type', 'Unknown')
                    if activity_type == 'Run':
                        color = 'green'
                    elif activity_type == 'TrailRun':
                        color = 'blue'
                    elif activity_type == 'Swim':
                        color = 'cyan'
                    elif activity_type == 'HighIntensityIntervalTraining':
                        activity_type = 'HIIT'
                        color = 'red'
                    elif activity_type == 'Tennis':
                        color = 'gray'
                    else:
                        color = 'purple'
                    st.markdown(
                        f"""
                        <div style='
                            display: inline-block;
                            background-color: white;
                            color: {color};
                            padding: 5px 10px;
                            border-radius: 15px;
                            font-weight: bold;
                        '>
                            {activity_type}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    st.write(f"**{past_activity['name']}** - {past_activity['start_date_local'][:10]}")
                    st.write(f"Distance: {past_activity['distance']/1000:.2f} km")
                    st.write(f"Duration: {past_activity['moving_time']/60:.0f} min")
                    st.write(f"Elevation: {past_activity['total_elevation_gain']:.0f} m")
                    # storage.add_activity(athlete_id, activity_detail,str_summary)
                    if past_activity['is_coached'] == False:
                        st.write(":red-background[You have not yet received a coaching for this activity!]")
                        if st.button('Analyse!', key=f"analyze_{index}"):
                            if credits > 0:
                                #storage.update_activity_coaching(athlete_id, past_activity['id'], True)
                                activity_detail = get_activity_details(access_token, past_activity['activity_id'])
                                summary = extract_activity_summary(activity_detail)
                                str_summary = format_activity_for_prompt(summary)

                                print(f"str_summary : {str_summary}")
                                coach_feedback = generate_content(input_text=str_summary,athlete_id=athlete_id,prompt=str(preferences),activity_id=past_activity['activity_id'])
                                with st.spinner("Analyse in progress...",show_time=True):
                                    time.sleep(3)
                                coach_feedback = remove_character(coach_feedback,'###')
                                coach_feedback = remove_character(coach_feedback,'**')
                                st.session_state.credits -=1
                                st.session_state.used_credits += 1
                                st.session_state.is_coached = True
                                update_activity_by_id(access_token=access_token,activity_id=past_activity['activity_id'],description=coach_feedback + " \n\n\n 💪Powered by WildStride💪")
                                st.success(f"Analyse done!")
                                with st.popover("See my analysis"):
                                    st.write(coach_feedback)

                            else:
                                st.error("Not enough credits")
                    else :
                        with st.popover("See my analysis"):
                            st.write(past_activity['coach_feedback'])

                    st.markdown("---")  # Add a horizontal line for separation

            st.subheader("Activity Type Repartition")
            activity_type_counts = df['sport_type'].value_counts().reset_index()
            activity_type_counts.columns = ['Activity Type', 'Count']
            pie_chart = alt.Chart(activity_type_counts).mark_arc().encode(
                theta=alt.Theta(field="Count", type="quantitative"),
                color=alt.Color(field="Activity Type", type="nominal"),
                tooltip=['Activity Type', 'Count']
            )
            st.altair_chart(pie_chart, use_container_width=True)

            # Evolution of Distance, Duration, and Elevation
            st.subheader("Evolution of Distance, Duration, and Elevation")
            df['start_date_local'] = pd.to_datetime(df['start_date_local'])
            df = df.sort_values('start_date_local')
            df['Distance (m)'] = df['distance'] / 100
            df['Duration (min)'] = df['moving_time'] / 60
            df['Elevation (m)'] = df['total_elevation_gain']

            line_chart = alt.Chart(df).transform_fold(
                ['Distance (m)', 'Duration (min)', 'Elevation (m)'],
                as_=['Metric', 'Value']
            ).mark_line().encode(
                x='date:T',
                y='Value:Q',
                color='Metric:N',
                tooltip=['date:T', 'Metric:N', 'Value:Q']
            )
            st.altair_chart(line_chart, use_container_width=True)

        else:
            st.error("❌ Failed to retrieve access token 2.")
else:
    # background_image_url = "https://woody.cloudly.space/app/uploads/lesportesdusoleil/2022/11/thumbs/Z72_0900-HD-1920px-Web-%C2%A9-EVOQ-1920x960.jpg"  # Replace with your image URL or local path

    background_image_url = "https://i.imgur.com/ihSLyuK.jpeg"
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("{background_image_url}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;

        }}
        .login-link {{
            font-size: 24px;
            font-weight: bold;
            color: #FF4B4B;
            text-decoration: none;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    strava_login_url = get_strava_auth_url()

    # Create a button with orange background and white text
    button_html = f"""
        <style>
        a:link, a:visited {{
            color: white;
            font-weight: bold;
        }}

        .login-button {{
            background-color: #fc4c02;
            text-color: white;
            padding: 10px 20px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 24px;
            margin: 4px 2px;
            cursor: pointer;
            border: none;
            border-radius: 12px;
        }}
        </style>
        <a href='{strava_login_url}' class='login-button'>LOGIN WITH STRAVA</a>
    """


    access_token, athlete_id = get_valid_token(st.session_state.athlete_id)
    st.title("WELCOME TO WILDSTRIDE")
    st.title("Start your journey to become a better runner with our AI coach.")

    st.write("Connect your Strava account and let our AI analyze your activities to give you **personalized, goal-driven coaching advice** you won’t find on Strava or Garmin.")
    st.write("Each coaching session uses credits. You can earn more by:")
    st.markdown("- 💬 Recommending WildStride to friends using your **referral code**")
    st.markdown("- ✉️ Sharing feedback or suggestions at [contact.wildstride@gmail.com](contact.wildstride@gmail.com)")
    st.write("Ready to level up your training? Start by connecting your Strava account below.")
    st.markdown(button_html, unsafe_allow_html=True)
    st.write("Made with ❤️ by Jettz, engineering runner")
    st.write("Contact us at contact.wildstride@gmail.com")
