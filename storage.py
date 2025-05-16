from datetime import datetime
from typing import Dict, List, Optional
import os
from supabase import create_client, Client
import streamlit as st
from activities_parsing import generate_user_identifier

class Storage:
    def __init__(self):
        # Initialize Supabase client
        self.supabase: Client = create_client(
            st.secrets["supabase_url"],
            st.secrets["supabase_key"]
        )
        self._ensure_tables()

    def _ensure_tables(self):
        """Ensure tables exist (Supabase will create them automatically)"""
        pass  # Tables are managed through Supabase dashboard

    def _extract_stats_from_totals(self, totals: Dict) -> Dict:
        """Extract relevant statistics from Strava totals"""
        return {
            'total_activities': totals.get('count', 0),
            'total_distance': totals.get('distance', 0),
            'total_elevation': totals.get('elevation_gain', 0)
        }

    def save_user_data(self, athlete_id: str, data: Dict) -> None:
        """Save user data to Supabase"""
        # Update preferences
        if 'preferences' in data:
            self.supabase.table('user_preferences').upsert({
                'athlete_id': athlete_id,
                'preferences': data['preferences'],
                'updated_at': datetime.now().isoformat()
            }).execute()

        # Update activities if present
        if 'activities' in data:
            for activity in data['activities']:
                self.supabase.table('activities').upsert({
                    'athlete_id': athlete_id,
                    'activity_id': activity['id'],
                    'name': activity['name'],
                    'start_date_local': activity['date'],
                    'type': activity['type'],
                    'distance': activity['distance'],
                    'moving_time': activity['moving_time'],
                    'total_elevation_gain': activity['total_elevation_gain'],
                    'updated_at': datetime.now().isoformat()
                }).execute()

    def get_user_data(self, athlete_id: str) -> Optional[Dict]:
        """Get user data from Supabase"""
        # Get preferences
        preferences = self.supabase.table('user_preferences') \
            .select('preferences') \
            .eq('athlete_id', athlete_id) \
            .execute()

        # Get activities
        activities = self.supabase.table('activities') \
            .select('*') \
            .eq('athlete_id', athlete_id) \
            .order('start_date_local', desc=True) \
            .limit(10) \
            .execute()

        athletes_info = self.supabase.table('athletes') \
            .select('*') \
            .eq('athlete_id', athlete_id) \
            .execute()

        if not preferences.data and not activities.data:
            return None

        return {
            'preferences': preferences.data[0]['preferences'] if preferences.data else {},
            'activities': activities.data if activities.data else [],
            'athletes_info': athletes_info.data[0] if athletes_info.data else {}
        }

    def update_user_preferences(self, athlete_id: str, preferences: Dict) -> None:
        """Update user preferences"""
        self.supabase.table('user_preferences').upsert({
            'athlete_id': athlete_id,
            'preferences': preferences,
            'updated_at': datetime.now().isoformat()
        }).execute()

    def add_activity(self, athlete_id: str, activity: Dict, summary: str) -> None:
        """Add an activity to user's history with additional fields"""
        self.supabase.table('activities') \
            .upsert(
                {
                    'athlete_id': athlete_id,
                    'activity_id': str(activity['id']),  # Convert to string to ensure consistency
                    'name': activity['name'],
                    'start_date_local': activity['start_date_local'],
                    'sport_type': activity['sport_type'],
                    'distance': activity['distance'],
                    'moving_time': activity['moving_time'],
                    'total_elevation_gain': activity['total_elevation_gain'],
                    'average_speed': activity.get('average_speed'),
                    'average_cadence': activity.get('average_cadence'),
                    'average_watts': activity.get('average_watts'),
                    'average_heartrate': activity.get('average_heartrate'),
                    'max_heartrate': activity.get('max_heartrate'),
                    'suffer_score': activity.get('suffer_score'),
                    'updated_at': datetime.now().isoformat(),
                    'summary': summary
                },
                on_conflict='athlete_id,activity_id'  # Specify the unique constraint
            ).execute()

    def update_activity_coach(self, athlete_id: str, activity_id: str, coach_feedback:str) -> None:
        """Add an activity to user's history"""
        self.supabase.table('activities') \
            .upsert(
                {
                    'athlete_id': athlete_id,
                    'activity_id': activity_id,
                    'coach_feedback' : coach_feedback,
                    'is_coached' : True,
                    'updated_at': datetime.now().isoformat()
                },
                on_conflict='athlete_id,activity_id'  # Specify the unique constraint
            ).execute()

    def get_user_activities(self, athlete_id: str) -> List[Dict]:
        """Get user's stored activities"""
        result = self.supabase.table('activities') \
            .select('*') \
            .eq('athlete_id', athlete_id) \
            .order('start_date_local', desc=True) \
            .limit(20) \
            .execute()
        return result.data if result.data else []

    def update_athlete(self, athlete_data: Dict) -> None:
        """Update or create athlete profile"""
        self.supabase.table('athletes').upsert({
            'athlete_id': str(athlete_data['id']),
            'firstname': athlete_data.get('firstname'),
            'lastname': athlete_data.get('lastname'),
            'city': athlete_data.get('city'),
            'country': athlete_data.get('country'),
            'profile_url': athlete_data.get('profile'),
            'updated_at': datetime.now().isoformat(),
            'ref_code' : generate_user_identifier(athlete_data.get('firstname'), athlete_data.get('lastname'), athlete_data.get('id'))
        }).execute()

    def update_athlete_used_ref_code(self,athlete_id: str, used_ref_code: str) -> None:
        """Update or create athlete profile"""
        self.supabase.table('athletes').update({'used_ref_code': used_ref_code}).eq('athlete_id', athlete_id).execute()

    def update_athlete_stats(self, athlete_id: str, stats: Dict) -> None:
        """Update athlete statistics with the new structure"""
        # Process all-time stats for each activity type
        stats_to_update = []
        for activity_type in ['run', 'ride']:
            # All-time stats
            totals_key = f'all_{activity_type}_totals'
            if totals_key in stats:
                stats_data = self._extract_stats_from_totals(stats[totals_key])
                stats_to_update.append({
                    'athlete_id': athlete_id,
                    'period': 'all_time',
                    'activity_type': activity_type,
                    'total_activities': stats_data['total_activities'],
                    'total_distance': stats_data['total_distance'],
                    'total_elevation': stats_data['total_elevation'],
                    'updated_at': datetime.now().isoformat()
                })

            # Year-to-date stats
            totals_key = f'ytd_{activity_type}_totals'
            if totals_key in stats:
                stats_data = self._extract_stats_from_totals(stats[totals_key])
                stats_to_update.append({
                    'athlete_id': athlete_id,
                    'period': 'ytd',
                    'activity_type': activity_type,
                    'total_activities': stats_data['total_activities'],
                    'total_distance': stats_data['total_distance'],
                    'total_elevation': stats_data['total_elevation'],
                    'updated_at': datetime.now().isoformat()
                })

        # Update stats one by one to ensure proper upsert behavior
        if stats_to_update:
            for stat in stats_to_update:
                self.supabase.table('athlete_stats') \
                    .upsert(stat, on_conflict='athlete_id,period,activity_type') \
                    .execute()

    def get_athlete_stats(self, athlete_id: str) -> Dict[str, Dict]:
        """Get athlete statistics organized by period and activity type"""
        result = self.supabase.table('athlete_stats') \
            .select('*') \
            .eq('athlete_id', athlete_id) \
            .execute()

        if not result.data:
            return {}

        # Organize stats by period and activity type
        organized_stats = {'all_time': {}, 'ytd': {}}
        for stat in result.data:
            period = stat['period']
            activity_type = stat['activity_type']
            organized_stats[period][activity_type] = {
                'total_activities': stat['total_activities'],
                'total_distance': stat['total_distance'],
                'total_elevation': stat['total_elevation']
            }

        return organized_stats

    def save_strava_tokens(self, athlete_id: str, tokens: Dict) -> None:
        """Save Strava access and refresh tokens"""
        try:
            # Ensure all required fields are present
            token_data = {
                'athlete_id': athlete_id,
                'access_token': tokens.get('access_token'),
                'refresh_token': tokens.get('refresh_token'),
                'expires_at': int(tokens.get('expires_at', 0)),  # Ensure it's an integer
                'updated_at': datetime.now().isoformat()
            }

            # Validate token data
            if not all([token_data['access_token'], token_data['refresh_token'], token_data['expires_at']]):
                print("Missing required token data")
                return

            print(f"Saving tokens for athlete {athlete_id}")
            print(f"Expires at: {token_data['expires_at']}")

            self.supabase.table('strava_tokens').upsert(
                token_data,
                on_conflict='athlete_id'
            ).execute()

        except Exception as e:
            print(f"Error saving tokens: {str(e)}")

    def get_strava_tokens(self, athlete_id: str) -> Optional[Dict]:
        """Get Strava tokens for an athlete"""
        try:
            result = self.supabase.table('strava_tokens') \
                .select('*') \
                .eq('athlete_id', athlete_id) \
                .execute()

            if result.data:
                token_data = result.data[0]
                print(f"Retrieved tokens for athlete {athlete_id}")
                print(f"Expires at: {token_data.get('expires_at')}")
                return token_data

            print(f"No tokens found for athlete {athlete_id}")
            return None

        except Exception as e:
            print(f"Error retrieving tokens: {str(e)}")
            return None

    def update_user_credits(self, athlete_id: str, credits: int, used_credits: int) -> None:
        """Update the credits and used_credits for a specific user"""
        self.supabase.table('athletes').update({'credits': credits, 'used_credits': used_credits}).eq('athlete_id', athlete_id).execute()
