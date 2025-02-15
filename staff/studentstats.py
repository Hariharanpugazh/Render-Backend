from django.http import JsonResponse
from pymongo import MongoClient

def studentstats(request, regno):
    client = MongoClient('mongodb+srv://krish:krish@assessment.ar5zh.mongodb.net/')
    db = client['test_portal_db']

    # Fetch student data
    student_data = db.students.find_one({"regno": regno})
    if not student_data:
        return JsonResponse({"error": "Student not found"}, status=404)

    student_id = str(student_data["_id"])  # Convert ObjectId to string

    # Fetch contest data visible to the student
    contest_data = db.coding_assessments.find({"visible_to": regno}, {"_id": 0})
    contest_list = list(contest_data)

    # Fetch all contest IDs visible to the student
    contest_ids = [contest.get("contestId") for contest in contest_list if contest.get("contestId")]

    # Fetch coding report for contests relevant to the student
    coding_reports = db.coding_report.find({"contest_id": {"$in": contest_ids}})
    coding_report_map = {report["contest_id"]: report for report in coding_reports}

    # Determine test statuses
    completed_tests = 0
    in_progress_tests = 0

    for contest_id in contest_ids:
        report = coding_report_map.get(contest_id)

        if not report:
            # No report means the test is in progress
            in_progress_tests += 1
        else:
            # Find the status for the current student
            student_status = None
            for student in report["students"]:
                if str(student["student_id"]) == student_id:
                    student_status = student.get("status")
                    break

            if student_status == "Completed":
                completed_tests += 1
            else:
                in_progress_tests += 1

    # Response with all assessment details
    assessments = []
    for contest in contest_list:
        assessment_overview = contest.get("assessmentOverview", {})
        problems = []
        contest_status = "Yet to Start"  # Default status for contest

        # Check the contest status based on the coding report
        report = coding_report_map.get(contest.get("contestId"))
        if report:
            for student in report["students"]:
                if str(student["student_id"]) == student_id:
                    contest_status = student.get("status", "Pending")  # Get the contest status
                    break

        # Handle problems based on contest status
        if contest_status == "Completed":
            for student in report["students"]:
                if str(student["student_id"]) == student_id:
                    attended_questions = student.get("attended_question", [])
                    for attended_problem in attended_questions:
                        problems.append({
                            "title": attended_problem.get("title", ""),
                            "result": attended_problem.get("result", ""),
                            "level": attended_problem.get("level", ""),
                            "problem_statement": attended_problem.get("problem_statement", "")
                        })
                    break
        elif contest_status == "Pending":
            problems = "Pending"
        else:  # Yet to Start
            problems = "No problems yet"

        # Add assessment details for this contest
        assessments.append({
            "contestId": contest.get("contestId", ""),
            "name": assessment_overview.get("name", ""),
            "description": assessment_overview.get("description", ""),
            "registrationStart": assessment_overview.get("registrationStart", ""),
            "registrationEnd": assessment_overview.get("registrationEnd", ""),
            "guidelines": assessment_overview.get("guidelines", ""),
            "questions": contest.get("testConfiguration", {}).get("questions", ""),
            "duration": contest.get("testConfiguration", {}).get("duration", ""),
            "passPercentage": contest.get("testConfiguration", {}).get("passPercentage", ""),
            "problems": problems,
            "contestStatus": contest_status  # Added contest status
        })

    response_data = {
        "student": {
            "student_id": student_id,  # Include student_id
            "name": student_data.get("name", ""),
            "email": student_data.get("email", ""),
            "collegename": student_data.get("collegename", ""),
            "dept": student_data.get("dept", ""),
            "regno": regno,
            "year": student_data.get("year", ""),
        },
        "performance": {
            "total_tests": len(contest_ids),
            "completed_tests": completed_tests,
            "in_progress_tests": in_progress_tests,
            "average_score": 0,  # Placeholder for average score logic
        },
        "assessments": assessments
    }

    return JsonResponse(response_data)


def mcq_student_results(request, regno):
    client = MongoClient('mongodb+srv://krish:krish@assessment.ar5zh.mongodb.net/')
    db = client['test_portal_db']

    # Fetch student data
    student_data = db.students.find_one({"regno": regno})
    if not student_data:
        return JsonResponse({"error": "Student not found"}, status=404)

    student_id = str(student_data["_id"])  # Convert ObjectId to string

    # Fetch MCQ assessment data visible to the student
    mcq_assessments = db.MCQ_Assessment_Data.find({"visible_to": regno}, {"_id": 0})
    mcq_list = list(mcq_assessments)

    # Create a set of visible contest IDs for O(1) lookup
    visible_contest_ids = {mcq.get("contestId") for mcq in mcq_list if mcq.get("contestId")}

    # Fetch MCQ report for contests relevant to the student
    mcq_reports = db.MCQ_Assessment_report.find({"contest_id": {"$in": list(visible_contest_ids)}})
    # Only include reports for visible contests
    mcq_report_map = {
        report["contest_id"]: report 
        for report in mcq_reports 
        if report["contest_id"] in visible_contest_ids
    }

    # Initialize counters
    completed_tests = 0
    in_progress_tests = 0
    total_percentage = 0
    scored_tests = 0

    for contest_id in visible_contest_ids:
        report = mcq_report_map.get(contest_id)
        if not report or "students" not in report:  # Check if report exists and has students field
            # No report or no students field means the test is in progress
            in_progress_tests += 1
            continue

        # Find the status for the current student
        student_found = False
        for student in report["students"]:
            if str(student.get("student_id")) == student_id:
                student_found = True
                student_status = student.get("status")
                if student_status == "Completed":
                    completed_tests += 1
                    # Add percentage to total if available
                    percentage = student.get("percentage", 0)
                    total_percentage += percentage
                    scored_tests += 1
                break
        
        if not student_found:
            in_progress_tests += 1

    # Calculate average score
    average_score = (total_percentage / scored_tests) if scored_tests > 0 else 0

    # Response with all assessment details
    assessments = []
    for mcq in mcq_list:
        contest_id = mcq.get("contestId")
        # Skip if contest_id is missing or empty
        if not contest_id:
            continue
            
        assessment_overview = mcq.get("assessmentOverview", {})
        # Skip if required fields are missing or empty
        if not (assessment_overview.get("name") and 
                assessment_overview.get("description") and
                assessment_overview.get("registrationStart") and
                assessment_overview.get("registrationEnd")):
            continue

        problems = []
        contest_status = "Yet to Start"  # Default status for contest
        percentage = 0  # Default percentage for the contest

        # Check the contest status based on the MCQ report
        report = mcq_report_map.get(contest_id)
        if report and "students" in report:  # Add check for students key
            for student in report["students"]:
                if str(student.get("student_id")) == student_id:
                    contest_status = student.get("status", "Pending")  # Get the contest status
                    percentage = student.get("percentage", 0)  # Get the percentage
                    break

        # Handle problems based on contest status
        if contest_status == "Completed" and report and "students" in report:  # Add check for students key
            for student in report["students"]:
                if str(student.get("student_id")) == student_id:
                    attended_questions = student.get("attended_question", [])
                    for attended_problem in attended_questions:
                        problems.append({
                            "title": attended_problem.get("title", ""),
                            "student_answer": attended_problem.get("student_answer", ""),
                            "correct_answer": attended_problem.get("correct_answer", "")
                        })
                    break
        elif contest_status == "Pending":
            problems = "Pending"
        else:  # Yet to Start
            problems = "No problems yet"

        # Add assessment details for this MCQ contest
        assessments.append({
            "contestId": contest_id,
            "name": assessment_overview.get("name", ""),
            "description": assessment_overview.get("description", ""),
            "registrationStart": assessment_overview.get("registrationStart", ""),
            "registrationEnd": assessment_overview.get("registrationEnd", ""),
            "guidelines": assessment_overview.get("guidelines", ""),
            "questions": mcq.get("testConfiguration", {}).get("questions", ""),
            "duration": mcq.get("testConfiguration", {}).get("duration", ""),
            "passPercentage": mcq.get("testConfiguration", {}).get("passPercentage", ""),
            "problems": problems,
            "contestStatus": contest_status,
            "percentage": percentage
        })

    response_data = {
        "student": {
            "student_id": student_id,
            "name": student_data.get("name", ""),
            "email": student_data.get("email", ""),
            "collegename": student_data.get("collegename", ""),
            "dept": student_data.get("dept", ""),
            "regno": regno,
        },
        "performance": {
            "total_tests": len(visible_contest_ids),
            "completed_tests": completed_tests,
            "in_progress_tests": in_progress_tests,
            "average_score": round(average_score, 2),
        },
        "assessments": assessments
    }

    return JsonResponse(response_data)