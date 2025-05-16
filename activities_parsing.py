from datetime import datetime

def extract_activity_summary(activity: dict) -> dict:
    def fmt_pace(speed_mps):
        return f"{int(1000 / speed_mps) // 60}:{int(1000 / speed_mps) % 60:02d} min/km" if speed_mps else "N/A"

    def format_splits(splits):
        return [
            {
                "split": s["split"],
                "distance_km": round(s["distance"] / 1000, 2),
                "time_min": round(s["moving_time"] / 60, 2),
                "elevation_gain_m": s.get("elevation_difference", 0),
                "avg_hr": round(s.get("average_heartrate", 0), 1),
                "avg_speed": round(s["average_speed"], 2),
                "pace": fmt_pace(s["average_speed"])
            }
            for s in splits
        ]

    def format_segments(segments):
        return [
            {
                "name": s["name"],
                "distance_m": round(s["distance"], 1),
                "average_grade": s["segment"].get("average_grade"),
                "avg_hr": round(s.get("average_heartrate", 0), 1),
                "avg_watts": round(s.get("average_watts", 0), 1),
                "pace": fmt_pace(s.get("average_speed", 0)),
            }
            for s in segments
        ]

    return {
        "name": activity["name"],
        "sport_type": activity["sport_type"],
        "date": activity["start_date_local"][:10],
        "description": activity.get("description", ""),
        "distance_km": round(activity["distance"] / 1000, 2),
        "duration_min": round(activity["moving_time"] / 60, 1),
        "elevation_gain_m": round(activity["total_elevation_gain"], 1),
        "average_speed_mps": round(activity["average_speed"], 2),
        "pace": fmt_pace(activity["average_speed"]),
        "average_heart_rate": round(activity.get("average_heartrate", 0), 1),
        "max_heart_rate": round(activity.get("max_heartrate", 0), 1) if activity.get("max_heartrate", 0) is not None else 0.0,
        "average_cadence": round(activity.get("average_cadence", 0), 1)*2 if activity.get("average_cadence", 0) is not None else 0.0,
        "average_watts": round(activity.get("average_watts", 0), 1) if activity.get("average_watts", 0) is not None else 0.0,
        "suffer_score": activity.get("suffer_score", None),
        "calories": activity.get("calories", None),
        "splits": format_splits(activity.get("splits_metric", [])),
        "segments": format_segments(activity.get("segment_efforts", [])),
        "device_name": activity.get("device_name", "Unknown")
    }


def format_activity_for_prompt(summary: dict) -> str:
    lines = []

    lines.append(f"🏃 **Activity Name:** {summary['name']}")
    lines.append(f"📅 **Date:** {summary['date']}")
    lines.append(f"🏷️ **Type:** {summary['sport_type']}")
    lines.append(f"📝 **Description:** {summary['description']}\n")

    lines.append(f"📏 **Distance:** {summary['distance_km']} km")
    lines.append(f"⏱️ **Duration:** {summary['duration_min']} min")
    lines.append(f"⛰️ **Elevation Gain:** {summary['elevation_gain_m']} m")
    lines.append(f"🚀 **Pace:** {summary['pace']}")
    lines.append(f"❤️ **Avg HR:** {summary['average_heart_rate']} bpm | **Max HR:** {summary['max_heart_rate']} bpm")
    lines.append(f"⚙️ **Cadence:** {summary['average_cadence']} spm")
    lines.append(f"⚡ **Avg Watts:** {summary['average_watts']}")
    lines.append(f"🔥 **Suffer Score:** {summary['suffer_score']}")
    lines.append(f"🔋 **Calories:** {summary['calories']}")
    lines.append(f"📟 **Device:** {summary['device_name']}\n")

    # Splits
    if summary["splits"]:
        lines.append("📊 **Splits:**")
        for split in summary["splits"]:
            lines.append(
                f" - Split {split['split']}: {split['distance_km']} km in {split['time_min']} min "
                f"(Pace: {split['pace']}, HR: {split['avg_hr']} bpm, Elev: {split['elevation_gain_m']} m)"
            )

    # Segments
    if summary["segments"]:
        lines.append("\n📍 **Segment Efforts:**")
        for seg in summary["segments"]:
            lines.append(
                f" - {seg['name']}: {seg['distance_m']} m @ {seg['average_grade']}% "
                f"(HR: {seg['avg_hr']} bpm, Watts: {seg['avg_watts']}, Pace: {seg['pace']})"
            )

    return "\n".join(lines)


import requests

def update_activity_by_id(access_token: str, activity_id: int, description: str = None, name: str = None):
    """
    Uses the Strava API to update an activity's fields using the updateActivityById operation.

    Args:
        access_token (str): The OAuth access token for the authenticated athlete.
        activity_id (int): The ID of the activity to update.
        description (str, optional): New description to set.
        name (str, optional): New name for the activity.

    Returns:
        dict: The updated activity object from the Strava API.
    """
    url = f"https://www.strava.com/api/v3/activities/{activity_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {}
    if description:
        payload["description"] = description[:1024]
    if name:
        payload["name"] = name[:100]  # Strava name limit

    response = requests.put(url, headers=headers, json=payload)

    if response.status_code == 200:
        print('DONE')
        return response.json()

    else:
        raise Exception(f"❌ Error updating activity: {response.status_code} - {response.text}")




def post_activity_comment(access_token: str, activity_id: int, comment_text: str) -> dict:
    """
    Posts a comment on a Strava activity using the API.

    Args:
        access_token (str): OAuth token of the authenticated user.
        activity_id (int): ID of the Strava activity to comment on.
        comment_text (str): The comment text (should be concise).

    Returns:
        dict: The API response containing the created comment object.
    """
    url = f"https://www.strava.com/api/v3/activities/{activity_id}/comments"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    payload = {
        "text": comment_text[:512]  # Safeguard for comment length
    }

    response = requests.post(url, headers=headers, data=payload)

    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"❌ Failed to post comment: {response.status_code} - {response.text}")

def generate_user_identifier(firstname: str, lastname: str, athlete_id: str) -> str:
    """Generate a unique identifier using the first and last letters of the first and last name, and the last two digits of the athlete ID."""
    if len(firstname) < 2 or len(lastname) < 2 or len(str(athlete_id)) < 2:
        raise ValueError("Inputs must be at least two characters long.")
    identifier = f"{firstname[0]}{firstname[-1]}{lastname[0]}{lastname[-1]}{str(athlete_id)[-2:]}"
    return identifier
