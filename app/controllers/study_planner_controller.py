from typing import List, Dict, Any
from datetime import date, datetime, time, timedelta
from ..models.study_plan import (
    Subject, Topic, StudySession, StudyDay, StudyPreferences,
    UserProfile, StudyPlanRequest, StudyPlanResponse
)


class StudyPlannerController:
    
    @staticmethod
    def generate_study_plan(plan_request: StudyPlanRequest) -> StudyPlanResponse:
        """
        Generate a rule-based personalized study plan based on subjects, exam dates, and user preferences.
        
        Rules:
        1. Subjects with exams in less than 5 days get at least 2 hours per day
        2. High importance subjects are studied daily
        3. Low importance subjects are studied only after high and medium are covered
        4. Each subject gets full revision 2 days before the exam
        """
        # Extract information from request
        subjects = plan_request.subjects
        start_date = plan_request.start_date
        end_date = plan_request.end_date
        preferences = plan_request.preferences
        
        # Calculate total study hours needed and available
        total_study_hours_needed = 0
        for subject in subjects:
            # Calculate hours for initial study
            subject_hours = sum(topic.estimated_hours for topic in subject.topics)
            
            # Add revision time if the subject has an exam date
            if subject.exam_date:
                # Add revision hours (half of the initial study time)
                subject_hours += subject_hours * 0.5
                
            total_study_hours_needed += subject_hours
        
        # Calculate available study hours
        available_study_hours = 0
        current_date = start_date
        
        while current_date <= end_date:
            # Skip break days
            if preferences.break_days and current_date in preferences.break_days:
                current_date += timedelta(days=1)
                continue
                
            # Determine if it's a weekday or weekend
            is_weekend = current_date.weekday() >= 5  # 5=Saturday, 6=Sunday
            
            # Add available hours for this day
            if is_weekend:
                available_study_hours += preferences.weekend_hours
            else:
                available_study_hours += preferences.weekday_hours
                
            current_date += timedelta(days=1)
        
        # Warning flag if we don't have enough time
        insufficient_time = available_study_hours < total_study_hours_needed
        
        # Generate daily schedule using rule-based approach
        days, unallocated_topics = StudyPlannerController._generate_rule_based_schedule(
            subjects, start_date, end_date, preferences
        )
        
        # Calculate actual study hours and distribution
        total_study_hours = sum(
            session.duration_hours 
            for day in days 
            for session in day.sessions
        )
        
        subjects_distribution = {}
        for day in days:
            for session in day.sessions:
                if session.subject not in subjects_distribution:
                    subjects_distribution[session.subject] = 0
                subjects_distribution[session.subject] += session.duration_hours
        
        return StudyPlanResponse(
            days=days,
            total_study_hours=total_study_hours,
            subjects_distribution=subjects_distribution,
            insufficient_time=insufficient_time,
            total_hours_needed=total_study_hours_needed,
            available_hours=available_study_hours,
            unallocated_topics=unallocated_topics
        )
    
    @staticmethod
    def _generate_rule_based_schedule(
        subjects: List[Subject],
        start_date: date,
        end_date: date,
        preferences: StudyPreferences
    ) -> tuple[List[StudyDay], List[Dict[str, str]]]:
        """
        Generate a rule-based study schedule based on the following rules:
        1. Subjects with exams in less than 5 days get at least 2 hours per day
        2. High importance subjects are studied daily
        3. Low importance subjects are studied only after high and medium are covered
        4. Each subject gets full revision 2 days before the exam
        """
        days = []
        unallocated_topics = []
        
        # Prepare study data structure
        subject_data = []
        for subject in subjects:
            topics = []
            for topic in subject.topics:
                topics.append({
                    "name": topic.name,
                    "hours_needed": topic.estimated_hours,
                    "remaining_hours": topic.estimated_hours,
                    "difficulty": topic.difficulty,
                    "completed": False
                })
            
            subject_data.append({
                "name": subject.name,
                "exam_date": subject.exam_date,
                "importance": subject.importance,
                "topics": topics,
                "current_topic_index": 0,
                "needs_revision": bool(subject.exam_date),
                "revision_completed": False,
                "subject_completed": False
            })
        
        # Track daily coverage of high importance subjects
        high_importance_coverage = {}
        
        # Process each day from start to end date
        current_date = start_date
        while current_date <= end_date:
            # Skip break days
            if preferences.break_days and current_date in preferences.break_days:
                current_date += timedelta(days=1)
                continue
            
            # Reset daily tracking of high importance subjects
            high_importance_coverage[current_date] = set()
            
            # Determine if it's a weekday or weekend
            is_weekend = current_date.weekday() >= 5  # 5=Saturday, 6=Sunday
            
            # Get available hours for this day
            available_hours = preferences.weekend_hours if is_weekend else preferences.weekday_hours
            
            # Create study sessions for the day
            day_sessions = []
            hours_left = available_hours
            
            # Start time - use 9 AM by default or adjust based on preferences
            current_time = time(9, 0)
            
            # Step 1: Apply Rule 1 - Prioritize subjects with exams in less than 5 days
            urgent_subjects = [
                s for s in subject_data 
                if s["exam_date"] and not s["subject_completed"] and
                (s["exam_date"] - current_date).days < 5 and s["exam_date"] >= current_date
            ]
            
            for subject in urgent_subjects:
                if hours_left < 0.5:
                    break
                    
                # Try to allocate at least 2 hours if possible
                target_hours = min(2.0, hours_left)
                
                # Check if the subject needs revision
                revision_day = subject["exam_date"] - timedelta(days=preferences.revision_days_before)
                needs_revision_today = current_date == revision_day and not subject["revision_completed"]
                
                if needs_revision_today:
                    # Rule 4: Full revision 2 days before exam
                    hours_used, current_time = StudyPlannerController._add_revision_session(
                        subject, current_date, current_time, target_hours, 
                        preferences.session_duration, preferences.break_duration, day_sessions
                    )
                    hours_left -= hours_used
                    subject["revision_completed"] = True
                else:
                    # Regular urgent study session
                    hours_used, current_time = StudyPlannerController._add_regular_session(
                        subject, current_date, current_time, target_hours,
                        preferences.session_duration, preferences.break_duration, day_sessions
                    )
                    hours_left -= hours_used
                
                # Mark this subject as covered for today
                if subject["importance"] == "High":
                    high_importance_coverage[current_date].add(subject["name"])
            
            # Step 2: Apply Rule 2 - High importance subjects need daily coverage
            high_imp_subjects = [
                s for s in subject_data 
                if s["importance"] == "High" and not s["subject_completed"] and
                s["name"] not in high_importance_coverage.get(current_date, set())
            ]
            
            for subject in high_imp_subjects:
                if hours_left < 0.5:
                    break
                
                # Allocate at least 1 hour for high importance subjects
                target_hours = min(1.0, hours_left)
                
                # Check for revision day
                if subject["exam_date"]:
                    revision_day = subject["exam_date"] - timedelta(days=preferences.revision_days_before)
                    needs_revision_today = current_date == revision_day and not subject["revision_completed"]
                    
                    if needs_revision_today:
                        # Rule 4: Full revision 2 days before exam
                        hours_used, current_time = StudyPlannerController._add_revision_session(
                            subject, current_date, current_time, target_hours,
                            preferences.session_duration, preferences.break_duration, day_sessions
                        )
                        hours_left -= hours_used
                        subject["revision_completed"] = True
                        continue
                
                # Regular high importance session
                hours_used, current_time = StudyPlannerController._add_regular_session(
                    subject, current_date, current_time, target_hours,
                    preferences.session_duration, preferences.break_duration, day_sessions
                )
                hours_left -= hours_used
                
                # Mark this subject as covered for today
                high_importance_coverage[current_date].add(subject["name"])
            
            # Step 3: Apply Rule 3 - Medium importance subjects before low
            medium_imp_subjects = [
                s for s in subject_data 
                if s["importance"] == "Medium" and not s["subject_completed"]
            ]
            
            for subject in medium_imp_subjects:
                if hours_left < 0.5:
                    break
                
                # Check for revision day
                if subject["exam_date"]:
                    revision_day = subject["exam_date"] - timedelta(days=preferences.revision_days_before)
                    needs_revision_today = current_date == revision_day and not subject["revision_completed"]
                    
                    if needs_revision_today:
                        # Rule 4: Full revision 2 days before exam
                        hours_used, current_time = StudyPlannerController._add_revision_session(
                            subject, current_date, current_time, hours_left,
                            preferences.session_duration, preferences.break_duration, day_sessions
                        )
                        hours_left -= hours_used
                        subject["revision_completed"] = True
                        continue
                
                # Regular medium importance session
                hours_used, current_time = StudyPlannerController._add_regular_session(
                    subject, current_date, current_time, hours_left,
                    preferences.session_duration, preferences.break_duration, day_sessions
                )
                hours_left -= hours_used
            
            # Step 4: Apply Rule 3 continued - Low importance subjects last
            low_imp_subjects = [
                s for s in subject_data 
                if s["importance"] == "Low" and not s["subject_completed"]
            ]
            
            for subject in low_imp_subjects:
                if hours_left < 0.5:
                    break
                
                # Check for revision day
                if subject["exam_date"]:
                    revision_day = subject["exam_date"] - timedelta(days=preferences.revision_days_before)
                    needs_revision_today = current_date == revision_day and not subject["revision_completed"]
                    
                    if needs_revision_today:
                        # Rule 4: Full revision 2 days before exam
                        hours_used, current_time = StudyPlannerController._add_revision_session(
                            subject, current_date, current_time, hours_left,
                            preferences.session_duration, preferences.break_duration, day_sessions
                        )
                        hours_left -= hours_used
                        subject["revision_completed"] = True
                        continue
                
                # Regular low importance session
                hours_used, current_time = StudyPlannerController._add_regular_session(
                    subject, current_date, current_time, hours_left,
                    preferences.session_duration, preferences.break_duration, day_sessions
                )
                hours_left -= hours_used
            
            # Add the day to the plan if it has sessions
            if day_sessions:
                days.append(StudyDay(date=current_date, sessions=day_sessions))
            
            # Move to next day
            current_date += timedelta(days=1)
            
            # Check for completed subjects and update their status
            for subject in subject_data:
                if subject["subject_completed"]:
                    continue
                    
                # Check if all topics are completed
                all_topics_done = all(
                    topic["remaining_hours"] <= 0.01 or topic["completed"]
                    for topic in subject["topics"]
                )
                
                # If exam date has passed or all topics are done and revision is completed (or not needed)
                if (subject["exam_date"] and subject["exam_date"] < current_date) or \
                   (all_topics_done and (subject["revision_completed"] or not subject["needs_revision"])):
                    subject["subject_completed"] = True
                    
                    # Add any remaining topics to unallocated list
                    for topic in subject["topics"]:
                        if topic["remaining_hours"] > 0.01 and not topic["completed"]:
                            unallocated_topics.append({
                                "subject": subject["name"],
                                "topic": topic["name"],
                                "hours_remaining": round(topic["remaining_hours"], 1)
                            })
        
        return days, unallocated_topics
    
    @staticmethod
    def _add_regular_session(
        subject: Dict[str, Any], 
        current_date: date, 
        current_time: time, 
        available_hours: float,
        max_session_duration: float,
        break_duration: float,
        day_sessions: List[StudySession]
    ) -> tuple[float, time]:
        """Add a regular study session for the subject and return hours used and updated time"""
        if subject["subject_completed"]:
            return 0.0, current_time
            
        # Find the current topic that needs work
        while subject["current_topic_index"] < len(subject["topics"]):
            topic = subject["topics"][subject["current_topic_index"]]
            
            if topic["remaining_hours"] <= 0.01 or topic["completed"]:
                # Move to next topic if current one is completed
                subject["current_topic_index"] += 1
                continue
            
            # Determine duration for this session
            session_duration = min(
                max_session_duration,
                available_hours,
                topic["remaining_hours"]
            )
            
            # Create session
            end_time_dt = datetime.combine(datetime.today(), current_time) + timedelta(hours=session_duration)
            end_time = end_time_dt.time()
            
            session = StudySession(
                subject=subject["name"],
                topic=topic["name"],
                date=current_date,
                start_time=current_time,
                end_time=end_time,
                duration_hours=session_duration,
                session_type="regular"
            )
            
            day_sessions.append(session)
            
            # Update remaining hours
            topic["remaining_hours"] -= session_duration
            
            # If topic is complete, mark it and move to next
            if topic["remaining_hours"] <= 0.01:
                topic["completed"] = True
                subject["current_topic_index"] += 1
            
            # Update time and add break if needed
            if available_hours - session_duration > 0.01:  # If we still have time after this session
                # Add a break
                break_end_dt = end_time_dt + timedelta(hours=break_duration)
                updated_time = break_end_dt.time()
                return session_duration + break_duration, updated_time
            else:
                return session_duration, end_time
        
        # If we reach here, all topics are complete
        subject["subject_completed"] = True
        return 0.0, current_time
    
    @staticmethod
    def _add_revision_session(
        subject: Dict[str, Any], 
        current_date: date, 
        current_time: time, 
        available_hours: float,
        max_session_duration: float,
        break_duration: float,
        day_sessions: List[StudySession]
    ) -> tuple[float, time]:
        """Add a revision session covering multiple topics and return hours used and updated time"""
        if subject["revision_completed"] or subject["subject_completed"]:
            return 0.0, current_time
        
        hours_used = 0.0
        remaining_time = available_hours
        current_session_time = current_time
        
        # Calculate time needed for brief revision of each completed topic
        total_topics = len([t for t in subject["topics"] if not t["completed"]])
        topics_to_revise = min(total_topics, 5)  # Limit to 5 topics per revision session
        
        if topics_to_revise == 0:
            return 0.0, current_time
        
        time_per_topic = min(0.5, remaining_time / topics_to_revise)  # 30 min per topic max
        
        # Create one session for each topic to revise
        topic_index = 0
        topics_revised = 0
        
        while topic_index < len(subject["topics"]) and topics_revised < topics_to_revise and remaining_time > 0.1:
            topic = subject["topics"][topic_index]
            
            # Determine duration for this topic's revision
            session_duration = min(
                max_session_duration,
                remaining_time,
                time_per_topic
            )
            
            if session_duration < 0.1:  # Skip if less than 6 minutes
                topic_index += 1
                continue
                
            # Create session
            end_time_dt = datetime.combine(datetime.today(), current_session_time) + timedelta(hours=session_duration)
            end_time = end_time_dt.time()
            
            session = StudySession(
                subject=subject["name"],
                topic=f"Revision: {topic['name']}",
                date=current_date,
                start_time=current_session_time,
                end_time=end_time,
                duration_hours=session_duration,
                session_type="revision"
            )
            
            day_sessions.append(session)
            
            # Update counters
            hours_used += session_duration
            remaining_time -= session_duration
            topics_revised += 1
            topic_index += 1
            
            # Update time and add break if needed
            if remaining_time > 0.1:
                # Add a break
                break_end_dt = end_time_dt + timedelta(hours=break_duration)
                current_session_time = break_end_dt.time()
                hours_used += break_duration
                remaining_time -= break_duration
            else:
                current_session_time = end_time
        
        # Mark revision as completed if enough topics were revised
        if topics_revised >= min(3, total_topics):
            subject["revision_completed"] = True
            
        return hours_used, current_session_time 