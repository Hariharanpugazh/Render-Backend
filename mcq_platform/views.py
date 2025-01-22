# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
import json
import jwt
import datetime
import csv
from io import StringIO
import logging
from bson.objectid import ObjectId
from rest_framework.exceptions import AuthenticationFailed  # Import this exception
from datetime import datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny  # Correct import for utcnow()
from rest_framework.response import Response
from rest_framework import status

# Initialize MongoDB client
client = MongoClient("mongodb+srv://ihub:ihub@test-portal.lcgyx.mongodb.net/test_portal_db?retryWrites=true&w=majority")
db = client["test_portal_db"]  # Replace with your database name
collection = db["MCQ_Assessment_Data"]
section_collection = db["MCQ_Assessment_Section_Data"]  # Replace with your collection name
assessment_questions_collection = db["MCQ_Assessment_Data"]
mcq_report_collection = db["MCQ_Assessment_report"]
coding_report_collection = db["coding_report"]

logger = logging.getLogger(__name__)

SECRET_KEY = "Rahul"
JWT_SECRET = 'test'
JWT_ALGORITHM = "HS256"

from datetime import datetime, timedelta
import jwt
from django.http import JsonResponse

@csrf_exempt
def start_contest(request):
    if request.method == "POST":
        try:
            # Parse the incoming request body
            data = json.loads(request.body)
            contest_id = data.get("contestId")
            if not contest_id:
                return JsonResponse({"error": "Contest ID is required"}, status=400)
            
            # Generate a JWT token
            payload = {
                "contestId": contest_id,
                "exp": datetime.utcnow() + timedelta(hours=1),  # Token valid for 1 hour
            }
            token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

            return JsonResponse({"token": token}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=400)



def generate_token(contest_id):
    payload = {
        "contest_id": contest_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # Token expiration
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def decode_token(token):
    print("Decode")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        contest_id = payload.get("contestId")  # Ensure correct key
        if not contest_id:
            raise ValueError("Invalid token: 'contestId' not found.")
        return contest_id
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token.")


from datetime import datetime

@csrf_exempt
def save_data(request):
    if request.method == "POST":
        try:
             # 1. Extract and decode the JWT token from cookies
            jwt_token = request.COOKIES.get("jwt")
            print(f"JWT Token: {jwt_token}")
            if not jwt_token:
                logger.warning("JWT Token missing in cookies")
                raise AuthenticationFailed("Authentication credentials were not provided.")

            try:
                decoded_token = jwt.decode(jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                logger.info("Decoded JWT Token: %s", decoded_token)
            except jwt.ExpiredSignatureError:
                logger.error("Expired JWT Token")
                raise AuthenticationFailed("Access token has expired. Please log in again.")
            except jwt.InvalidTokenError:
                logger.error("Invalid JWT Token")
                raise AuthenticationFailed("Invalid token. Please log in again.")

            staff_id = decoded_token.get("staff_user")
            if not staff_id:
                logger.warning("Invalid payload: 'staff_user' missing")
                raise AuthenticationFailed("Invalid token payload.")

            data = json.loads(request.body)
            data["staffId"] = staff_id
            contest_id = data.get("contestId")
            if not contest_id:
                return JsonResponse({"error": "contestId is required"}, status=400)

            # Check if 'assessmentOverview' exists and contains the necessary fields
            if "assessmentOverview" not in data or "registrationStart" not in data["assessmentOverview"] or "registrationEnd" not in data["assessmentOverview"]:
                return JsonResponse({"error": "'registrationStart' or 'registrationEnd' is missing in 'assessmentOverview'"}, status=400)

            # Log the incoming data for debugging
            # print("Incoming Data:", data)

            # Convert registrationStart and registrationEnd to datetime objects
            try:
                data["assessmentOverview"]["registrationStart"] = datetime.fromisoformat(data["assessmentOverview"]["registrationStart"])
                data["assessmentOverview"]["registrationEnd"] = datetime.fromisoformat(data["assessmentOverview"]["registrationEnd"])
            except ValueError as e:
                return JsonResponse({"error": f"Invalid date format: {str(e)}"}, status=400)

            collection.insert_one(data)
            return JsonResponse({"message": "Data saved successfully", "contestId": contest_id}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=400)

@csrf_exempt
def save_section_data(request):
    if request.method == "POST":
        try:
             # 1. Extract and decode the JWT token from cookies
            jwt_token = request.COOKIES.get("jwt")
            print(f"JWT Token: {jwt_token}")
            if not jwt_token:
                logger.warning("JWT Token missing in cookies")
                raise AuthenticationFailed("Authentication credentials were not provided.")

            try:
                decoded_token = jwt.decode(jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                logger.info("Decoded JWT Token: %s", decoded_token)
            except jwt.ExpiredSignatureError:
                logger.error("Expired JWT Token")
                raise AuthenticationFailed("Access token has expired. Please log in again.")
            except jwt.InvalidTokenError:
                logger.error("Invalid JWT Token")
                raise AuthenticationFailed("Invalid token. Please log in again.")

            staff_id = decoded_token.get("staff_user")
            if not staff_id:
                logger.warning("Invalid payload: 'staff_user' missing")
                raise AuthenticationFailed("Invalid token payload.")

            data = json.loads(request.body)
            data["staffId"] = staff_id
            contest_id = data.get("contestId")
            if not contest_id:
                return JsonResponse({"error": "contestId is required"}, status=400)

            # Check if 'assessmentOverview' exists and contains the necessary fields
            if "assessmentOverview" not in data or "registrationStart" not in data["assessmentOverview"] or "registrationEnd" not in data["assessmentOverview"]:
                return JsonResponse({"error": "'registrationStart' or 'registrationEnd' is missing in 'assessmentOverview'"}, status=400)

            # Log the incoming data for debugging
            print("Incoming Data:", data)

            # Convert registrationStart and registrationEnd to datetime objects
            try:
                data["assessmentOverview"]["registrationStart"] = datetime.fromisoformat(data["assessmentOverview"]["registrationStart"])
                data["assessmentOverview"]["registrationEnd"] = datetime.fromisoformat(data["assessmentOverview"]["registrationEnd"])
            except ValueError as e:
                return JsonResponse({"error": f"Invalid date format: {str(e)}"}, status=400)

            collection.insert_one(data)
            return JsonResponse({"message": "Data saved successfully", "contestId": contest_id}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=400)


@csrf_exempt
def save_question(request):
    if request.method == "POST":
        try:
            # Validate Authorization Header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JsonResponse({"error": "Authorization header missing or invalid."}, status=401)

            # Decode the token to get the contest_id
            token = auth_header.split(" ")[1]
            contest_id = decode_token(token)

            # Parse the request body
            data = json.loads(request.body)
            questions = data.get("questions", [])
            if not questions:
                return JsonResponse({"error": "No questions provided"}, status=400)

            # Check if the contest_id already exists
            assessment = assessment_questions_collection.find_one({"contestId": contest_id})
            if not assessment:
                # If the contest does not exist, create it
                print(f"Creating new contest entry for contest_id: {contest_id}")
                assessment_questions_collection.insert_one({
                    "contestId": contest_id,
                    "questions": []
                })
                assessment = {"contestId": contest_id, "questions": []}

            # Append new questions to the contest
            existing_questions = assessment.get("questions", [])
            question_ids = {q.get("question_id") for q in existing_questions}  # Get existing question IDs

            new_questions = []
            for question in questions:
                if question.get("question_id") not in question_ids:
                    new_questions.append(question)

            # Add only unique questions
            if new_questions:
                assessment_questions_collection.update_one(
                    {"contestId": contest_id},
                    {"$addToSet": {"questions": {"$each": new_questions}}}
                )

            return JsonResponse({
                "message": "Questions saved successfully!",
                "added_questions": new_questions
            }, status=200)

        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=401)
        except Exception as e:
            return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def get_questions(request):
    if request.method == "GET":
        print("GET request received")
        try:
            # Validate Authorization Header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                print("Authorization header missing or invalid")
                return JsonResponse({"error": "Unauthorized access"}, status=401)

            # Decode the token to get the contest_id
            token = auth_header.split(" ")[1]
            contest_id = decode_token(token)
            print(f"Decoded contest ID: {contest_id}")

            # Check if the contest exists in the database
            assessment = assessment_questions_collection.find_one({"contestId": contest_id})
            if not assessment:
                # If no contest found, create a new entry with an empty questions list
                print(f"Creating new contest entry for contest_id: {contest_id}")
                assessment_questions_collection.insert_one({
                    "contestId": contest_id,
                    "questions": []
                })
                assessment = {"contestId": contest_id, "questions": []}

            # Fetch the questions
            questions = assessment.get("questions", [])
            print(f"Fetched questions: {questions}")
            return JsonResponse({"questions": questions}, status=200)
        except ValueError as e:
            print(f"Authorization error: {str(e)}")
            return JsonResponse({"error": str(e)}, status=401)
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=400)

@csrf_exempt
def update_question(request):
    if request.method == "PUT":
        try:
            token = request.headers.get("Authorization").split(" ")[1]
            contest_id = decode_token(token)

            data = json.loads(request.body)
            question_id = data.get("question_id")

            result = assessment_questions_collection.update_one(
                {
                    "contest_id": contest_id,
                    "questions.question_id": question_id,
                },
                {
                    "$set": {
                        "questions.$.questionType": data.get("questionType", "MCQ"),
                        "questions.$.question": data.get("question", ""),
                        "questions.$.options": data.get("options", []),
                        "questions.$.correctAnswer": data.get("correctAnswer", ""),
                        "questions.$.mark": data.get("mark", 0),
                        "questions.$.negativeMark": data.get("negativeMark", 0),
                        "questions.$.randomizeOrder": data.get("randomizeOrder", False),
                    }
                }
            )

            if result.matched_count == 0:
                return JsonResponse({"error": "Question not found"}, status=404)

            return JsonResponse({"message": "Question updated successfully"})
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=401)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=400)


@csrf_exempt
def finish_contest(request):
    if request.method == "POST":
        try:
            # Validate Authorization Header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JsonResponse({"error": "Authorization header missing or invalid."}, status=401)

            # Decode the token to get the contest_id
            token = auth_header.split(" ")[1]
            contest_id = decode_token(token)

            # Get the list of questions from the request body
            data = json.loads(request.body)
            questions_data = data.get("questions", [])

            if not questions_data:
                return JsonResponse({"error": "No question data provided."}, status=400)

            # Retrieve the existing entry for the contest_id
            existing_entry = collection.find_one({"contestId": contest_id})

            if existing_entry:
                # Update the existing entry with the new questions data
                collection.update_one(
                    {"contestId": contest_id},
                    {"$set": {"questions": questions_data}}  # Save the entire questions data
                )
            else:
                # If no entry exists for this contest_id, create a new one with all the question data
                collection.insert_one({
                    "contestId": contest_id,
                    "questions": questions_data,  # Store the full question data here
                    "assessmentOverview": {},  # Preserve the structure
                    "testConfiguration": {}
                })

            return JsonResponse({"message": "Contest finished successfully!"}, status=200)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=401)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=400)


@csrf_exempt
def bulk_upload_questions(request):
    if request.method == "POST":
        try:
            # Validate Authorization Header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JsonResponse({"error": "Authorization header missing or invalid."}, status=401)

            # Decode the token to get the contest_id
            token = auth_header.split(" ")[1]
            contest_id = decode_token(token)

            # Retrieve the uploaded file
            file = request.FILES.get("file")
            if not file:
                return JsonResponse({"error": "No file uploaded"}, status=400)

            # Parse CSV content
            file_data = file.read().decode("utf-8")
            csv_reader = csv.DictReader(StringIO(file_data))
            questions = []

            for row in csv_reader:
                try:
                    logger.debug("Processing row: %s", row)
                    # Extract and validate fields
                    mark = int(row.get("mark", 0)) if row.get("mark") else 0
                    negative_mark = int(row.get("negative_marking", 0)) if row.get("negative_marking") else 0
                    # question_id = str(uuid4())  # Generate unique ID

                    question = {
                        # "questionId": question_id,
                        "questionType": "MCQ",  # Assuming MCQ for bulk upload
                        "question": row.get("question", "").strip(),
                        "options": [
                            row.get("option_1", "").strip(),
                            row.get("option_2", "").strip(),
                            row.get("option_3", "").strip(),
                            row.get("option_4", "").strip(),
                            row.get("option_5", "").strip(),
                            row.get("option_6", "").strip(),
                        ],
                        "correctAnswer": row.get("correct_answer", "").strip(),
                        "mark": mark,
                        "negativeMark": negative_mark,
                        "randomizeOrder": False,  # Default to False
                        "level": row.get("level", "easy").strip(),  # Default level to "easy"
                        "tags": row.get("tags", "").split(",") if row.get("tags") else [],  # Convert tags to list
                    }
                    questions.append(question)
                except Exception as e:
                    logger.error("Error processing row: %s", row)
                    logger.error("Error: %s", str(e))
                    return JsonResponse({"error": f"Error in row: {row}. Details: {str(e)}"}, status=400)

            # Log the parsed questions
            logger.debug("Parsed Questions: %s", questions)

            return JsonResponse({"questions": questions}, status=200)
        except ValueError as e:
            logger.error("ValueError: %s", str(e))
            return JsonResponse({"error": str(e)}, status=401)
        except Exception as e:
            logger.error("Exception: %s", str(e))
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=400)
@csrf_exempt
def publish_mcq(request):
    if request.method == 'POST':
        try:
            # Validate Authorization Header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JsonResponse({"error": "Authorization header missing or invalid."}, status=401)

            # Decode the token to get the contest_id
            token = auth_header.split(" ")[1]
            contest_id = decode_token(token)

            data = json.loads(request.body)
            print("contest_id: ",contest_id)

            selected_students = data.get('students', [])

            # Validate input
            if not contest_id:
                return JsonResponse({'error': 'Contest ID is required'}, status=400)
            if not isinstance(selected_students, list) or not selected_students:
                return JsonResponse({'error': 'No students selected'}, status=400)

            # Check if the contest document exists
            existing_document = collection.find_one({"contestId": contest_id})
            if not existing_document:
                return JsonResponse({'error': 'Contest not found'}, status=404)

            # Append questions and students to the existing document
            collection.update_one(
                {"contestId": contest_id},
                {
                    '$addToSet': {
                        'visible_to': {'$each': selected_students},  # Append new students
                    }
                }
            )

            return JsonResponse({'message': 'Questions and students appended successfully!'}, status=200)

        except Exception as e:
            return JsonResponse({'error': f'Error appending questions and students: {str(e)}'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import random

@csrf_exempt
def get_mcqquestions(request, contestId):
    if request.method == "GET":
        try:
            # Find the contest/assessment document based on the contest_id
            assessment = collection.find_one({"contestId": contestId})
            if not assessment:
                return JsonResponse(
                    {"error": f"No assessment found for contestId: {contestId}"}, status=404
                )

            # Extract the test configuration
            test_configuration = assessment.get("testConfiguration", {})
            
            # Safely extract the number of questions to fetch
            questions_value = test_configuration.get("questions", 0)
            try:
                num_questions_to_fetch = int(questions_value)
            except (ValueError, TypeError):
                num_questions_to_fetch = 0  # Default to 0 if the value is invalid

            # Get the full list of questions
            questions = assessment.get("questions", [])

            if not questions:
                return JsonResponse(
                    {"error": "No questions found for the given contestId."}, status=404
                )

            # Validate the number of questions to fetch
            if num_questions_to_fetch > len(questions):
                return JsonResponse(
                    {"error": "Number of questions requested exceeds available questions."},
                    status=400,
                )

            # Shuffle questions if specified in the configuration
            if test_configuration.get("shuffleQuestions", False):
                random.shuffle(questions)

            # Select only the required number of questions
            selected_questions = questions[:num_questions_to_fetch]

            # Shuffle options for each question if specified
            for question in selected_questions:
                if question.get("randomizeOrder", False):
                    random.shuffle(question["options"])

            # Format the response
            response_data = {
                "assessmentName": assessment["assessmentOverview"].get("name"),
                "duration": test_configuration.get("duration"),
                "questions": [
                    {
                        "text": question.get("question"),
                        "options": question.get("options"),
                        "mark": question.get("mark"),
                        "negativeMark": question.get("negativeMark"),
                    }
                    for question in selected_questions
                ],
            }

            return JsonResponse(response_data, safe=False, status=200)

        except Exception as e:
            return JsonResponse(
                {"error": f"Failed to fetch MCQ questions: {str(e)}"}, status=500
            )
    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)

@api_view(["GET"])
@permission_classes([AllowAny])  # Allow unauthenticated access for testing
def get_section_questions_for_contest(request, contest_id):
    """
    API to fetch questions from sections for a given contestId.
    """
    try:
        # Fetch MCQ tests where the contestId matches
        mcq_tests = list(assessment_questions_collection.find(
            {"contestId": contest_id},
            {"questions": 0, "correctAnswer": 0}  # Exclude fields not needed
        ))

        if not mcq_tests:
            return JsonResponse([], safe=False, status=200)  # Return an empty list if no tests are found

        # Extract and transform data
        formatted_data = []
        for test in mcq_tests:
            for section in test.get('sections', []):
                # Prepare duration in the required format
                duration = section.get('sectionDuration', {})
                if isinstance(duration, dict):
                    hours = duration.get('hours', 0)
                    minutes = duration.get('minutes', 0)
                else:
                    hours = duration // 60
                    minutes = duration % 60

                section_data = {
                    "sectionName": section.get('sectionName', ""),
                    "duration": {
                        "hours": str(hours),
                        "minutes": str(minutes)
                    },
                    "questions": []
                }

                # Process each question in the section
                for question in section.get('questions', []):
                    section_data["questions"].append({
                        "text": question.get("question", ""),
                        "options": question.get("options", []),
                        "mark": None,
                        "negativeMark": None
                    })

                formatted_data.append(section_data)
        return JsonResponse(formatted_data, safe=False, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def submit_mcq_assessment(request):
    if request.method == "POST":
        try:
            # Parse incoming request data
            data = json.loads(request.body)
            contest_id = data.get("contestId")
            answers = data.get("answers", {})
            fullscreen_warning = data.get("FullscreenWarning", 0)
            noise_warning = data.get("NoiseWarning", 0)
            tabswitch_warning = data.get("TabSwitchWarning", 0)
            face_warning = data.get("FaceWarning", 0)
            ispublish = data.get("ispublish", False)
            pass_percentage = data.get("passPercentage", 50)  # Default pass percentage
            student_id = data.get("studentId")

            # Validate required fields
            if not contest_id:
                return JsonResponse({"error": "Contest ID is required"}, status=400)
            if not answers:
                return JsonResponse({"error": "Answers are required"}, status=400)
            if not student_id:
                return JsonResponse({"error": "Student ID is required"}, status=400)

            # Fetch assessment from the database
            assessment = collection.find_one({"contestId": contest_id})
            if not assessment:
                return JsonResponse(
                    {"error": f"No assessment found for contestId: {contest_id}"},
                    status=404,
                )

            # Initialize counters and data
            correct_answers = 0
            total_questions = 0
            attended_questions = []

            # Process section-based or non-section-based questions
            sections = assessment.get("sections", [])
            if sections:  # Section-based logic
                for section in sections:
                    section_name = section.get("sectionName", "Unnamed Section")
                    for question in section.get("questions", []):
                        question_text = question.get("question")
                        correct_answer = question.get("answer")
                        student_answers = answers.get(section_name, {})
                        student_answer = student_answers.get(question_text)

                        # Include only attended questions
                        if student_answer is not None:
                            attended_questions.append({
                                "title": question_text,
                                "section": section_name,
                                "student_answer": student_answer,
                                "correct_answer": correct_answer,
                            })

                            # Increment counters
                            if student_answer == correct_answer:
                                correct_answers += 1
                            total_questions += 1
            else:  # Non-section-based logic
                questions = assessment.get("questions", [])
                for question in questions:
                    question_text = question.get("question")
                    correct_answer = question.get("correctAnswer")
                    student_answer = answers.get(question_text)

                    # Include only attended questions
                    if student_answer is not None:
                        attended_questions.append({
                            "title": question_text,
                            "student_answer": student_answer,
                            "correct_answer": correct_answer,
                        })

                        # Increment counters
                        if student_answer == correct_answer:
                            correct_answers += 1
                        total_questions += 1

            # Calculate percentage and grade
            percentage = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
            grade = "Pass" if percentage >= pass_percentage else "Fail"

            # Record start and finish time
            start_time = datetime.utcnow()
            finish_time = datetime.utcnow()

            # Prepare student data
            student_data = {
                "student_id": student_id,
                "status": "Completed",
                "grade": grade,
                "attended_question": attended_questions,
                "FullscreenWarning": fullscreen_warning,
                "NoiseWarning": noise_warning,
                "FaceWarning": face_warning,
                "TabSwitchWarning": tabswitch_warning,
                "startTime": start_time,
                "finishTime": finish_time,
            }

            # Insert or update report
            report = mcq_report_collection.find_one({"contest_id": contest_id})
            if not report:
                # Create a new report
                mcq_report_collection.insert_one({
                    "contest_id": contest_id,
                    "passPercentage": pass_percentage,
                    "students": [student_data],
                    "ispublish": ispublish,
                })
            else:
                # Check if the student already exists in the students array
                students = report.get("students", [])
                for student in students:
                    if student.get("student_id") == student_id:
                        student["status"] = "Completed"
                        student["grade"] = grade
                        student["attended_question"] = attended_questions
                        student["FullscreenWarning"] = fullscreen_warning
                        student["TabSwitchWarning"] = tabswitch_warning
                        student["NoiseWarning"] = noise_warning
                        student["FaceWarning"] = face_warning
                        student["startTime"] = student.get("startTime", start_time)
                        student["finishTime"] = finish_time
                        break
                else:
                    # Add a new student entry if not found
                    students.append(student_data)

                # Update the report with modified students array
                mcq_report_collection.update_one(
                    {"contest_id": contest_id},
                    {
                        "$set": {
                            "students": students,
                            "passPercentage": pass_percentage,
                            "ispublish": ispublish,
                        }
                    }
                )

            # Return the result
            return JsonResponse({
                "contestId": contest_id,
                "grade": grade,
                "percentage": percentage,
                "passPercentage": pass_percentage
            }, status=200)

        except Exception as e:
            return JsonResponse({"error": f"An error occurred: {str(e)}"}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def get_student_report(request, contestId, regno):
    if request.method == "GET":
        try:
            # Fetch the contest report
            report = mcq_report_collection.find_one({"contest_id": contestId})
            if not report:
                return JsonResponse({"error": f"No report found for contest_id: {contestId}"}, status=404)

            # Find the student in the report
            student_report = next(
                (student for student in report.get("students", []) if student["student_id"] == regno), None
            )
            if not student_report:
                return JsonResponse({"error": f"No report found for student with regno: {regno}"}, status=404)

            # Calculate the number of correct answers
            correct_answers = sum(
                1 for q in student_report.get("attended_question", []) if q.get("student_answer") == q.get("correct_answer")
            )

            # Format the response
            formatted_report = {
                "contest_id": contestId,
                "student_id": regno,
                "status": student_report.get("status"),
                "grade": student_report.get("grade"),
                "start_time": student_report.get("startTime"),
                "finish_time": student_report.get("finishTime"),
                "red_flags": student_report.get("warnings", 0),
                "fullscreen" : student_report.get("FullscreenWarning", 0),
                "facewarning": student_report.get("FaceWarning",0),
                "tabswitchwarning": student_report.get("TabSwitchWarning",0),
                "noisewarning": student_report.get("NoiseWarning",0),
                "attended_questions": [
                    {
                        "id": index + 1,
                        "question": q.get("title"),
                        "userAnswer": q.get("student_answer"),
                        "correctAnswer": q.get("correct_answer"),
                        "isCorrect": q.get("student_answer") == q.get("correct_answer"),
                    }
                    for index, q in enumerate(student_report.get("attended_question", []))
                    if q.get("student_answer") is not None
                ],
                "correct_answers": correct_answers,
                "passPercentage": report.get("passPercentage", 0),  # Include passPercentage
            }

            return JsonResponse(formatted_report, status=200, safe=False)

        except Exception as e:
            return JsonResponse({"error": f"Failed to fetch student report: {str(e)}"}, status=500)
    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)

@api_view(["POST"])
@permission_classes([AllowAny])  # Ensure only authorized users can access
def publish_result(request, contestId):
    try:
        # Validate the contest_id
        if not contestId:
            return JsonResponse({"error": "Contest ID is required"}, status=400)

        # Update the ispublish flag in the database
        result = mcq_report_collection.update_one(
            {"contest_id": contestId},
            {"$set": {"ispublish": True}}
        )

        result = coding_report_collection.update_one(
            {"contest_id": contestId},
            {"$set": {"ispublish": True}}
        )

        if result.modified_count == 0:
            return JsonResponse({"error": "Contest not found or already published"}, status=404)

        return JsonResponse({"message": "Results published successfully"}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)




students_collection = db["students"]  # Assuming you have a students collection

logger = logging.getLogger(__name__)

def decode_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        contest_id = payload.get("contestId")
        if not contest_id:
            raise ValueError("Invalid token: 'contestId' not found.")
        return contest_id
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token.")

@csrf_exempt
def publish_mcq(request):
    if request.method == 'POST':
        try:
            # Validate Authorization Header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JsonResponse({"error": "Authorization header missing or invalid."}, status=401)

            # Decode the token to get the contest_id
            token = auth_header.split(" ")[1]
            contest_id = decode_token(token)

            data = json.loads(request.body)
            print("contest_id: ", contest_id)

            selected_students = data.get('students', [])
            student_emails = data.get('studentEmails', [])  # Get student emails from the request

            # Validate input
            if not contest_id:
                return JsonResponse({'error': 'Contest ID is required'}, status=400)
            if not isinstance(selected_students, list) or not selected_students:
                return JsonResponse({'error': 'No students selected'}, status=400)
            if not isinstance(student_emails, list) or not student_emails:
                return JsonResponse({'error': 'No student emails provided'}, status=400)

            # Check if the contest document exists
            existing_document = collection.find_one({"contestId": contest_id})
            if not existing_document:
                return JsonResponse({'error': 'Contest not found'}, status=404)

            # Append questions and students to the existing document
            collection.update_one(
                {"contestId": contest_id},
                {
                    '$addToSet': {
                        'visible_to': {'$each': selected_students},  # Append new students
                    }
                }
            )

            # Fetch assessmentOverview details
            assessment_overview = existing_document.get("assessmentOverview", {})
            test_name = assessment_overview.get("name", "Unnamed Assessment")
            description = assessment_overview.get("description", "")
            registration_start = assessment_overview.get("registrationStart")
            registration_end = assessment_overview.get("registrationEnd")
            duration_dict = existing_document.get("testConfiguration", {}).get("duration", {})
            duration_hours = int(duration_dict.get("hours", 0))
            duration_minutes = int(duration_dict.get("minutes", 0))

            # Format date and time
            start_date = registration_start.strftime("%Y-%m-%d")
            start_time = registration_start.strftime("%H:%M:%S")
            end_date = registration_end.strftime("%Y-%m-%d")
            end_time = registration_end.strftime("%H:%M:%S")
            formatted_duration = f"{duration_hours} hours {duration_minutes} minutes"

            # Send email to each selected student
            for student_email in student_emails:
                # Fetch student details
                student = students_collection.find_one({"email": student_email})
                if not student:
                    logger.error(f"Student not found for email: {student_email}")
                    continue

                student_name = student.get("name", "Student")

                subject = f'Instructions for {test_name}'
                message = (
                    f'Dear {student_name},\n\n'
                    f'You are invited to participate in the {test_name}. Below are the details you need to know:\n\n'
                    f'Description: {description}\n'
                    f'Test Schedule: From {start_date}, {start_time} to {end_date}, {end_time}\n'
                    f'Duration: {formatted_duration}\n\n'
                    f'Please ensure you are prepared and available during the specified time window.\n\n'
                    f'If you have any questions or encounter any issues, feel free to contact us at {settings.DEFAULT_FROM_EMAIL}.\n\n'
                    f'Best of luck with your test!'
                )
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [student_email]
                send_mail(subject, message, from_email, recipient_list)

            return JsonResponse({'message': 'Questions and students appended successfully!'}, status=200)

        except ValueError as e:
            logger.error(f"ValueError: {str(e)}")
            return JsonResponse({'error': str(e)}, status=401)
        except Exception as e:
            logger.error(f"Exception: {str(e)}")
            return JsonResponse({'error': f'Error appending questions and students: {str(e)}'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
        


@csrf_exempt
def save_assessment_questions(request):
    if request.method == "POST":
        try:
            # Get JWT token from cookies
            jwt_token = request.COOKIES.get("jwt")
            if not jwt_token:
                return JsonResponse({"error": "Authentication required"}, status=401)

            try:
                decoded_token = jwt.decode(jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                staff_id = decoded_token.get("staff_user")
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
                return JsonResponse({"error": "Invalid or expired token"}, status=401)

            # Parse request data
            data = json.loads(request.body)
            section_name = data.get('sectionName')
            num_questions = data.get('numQuestions')
            section_duration = data.get('sectionDuration')
            mark_allotment = data.get('markAllotment')
            pass_percentage = data.get('passPercentage')
            time_restriction = data.get('timeRestriction')
            questions = data.get('questions', [])

            if not questions:
                return JsonResponse({"error": "No questions provided"}, status=400)

            # Find the latest assessment for this staff
            assessment = collection.find_one(
                {"staffId": staff_id},
                sort=[("_id", -1)]
            )

            if not assessment:
                return JsonResponse({"error": "No assessment found"}, status=404)

            # Format questions as per your schema
            formatted_questions = [{
                "question_type": "Multiple Choice",
                "question": q["question"],
                "options": q["options"],
                "answer": q["correctAnswer"] if "correctAnswer" in q else q["answer"]
            } for q in questions]

            # Update the document
            result = collection.update_one(
                {"_id": assessment["_id"]},
                {
                    "$push": {
                        "sections": {
                            "sectionName": section_name,
                            "numQuestions": num_questions,
                            "sectionDuration": section_duration,
                            "markAllotment": mark_allotment,
                            "passPercentage": pass_percentage,
                            "timeRestriction": time_restriction,
                            "questions": formatted_questions
                        }
                    },
                    "$inc": {"no_of_section": 1}
                }
            )

            if result.modified_count == 0:
                return JsonResponse({"error": "Failed to update assessment"}, status=400)

            return JsonResponse({
                "success": True,
                "message": "Questions saved successfully",
                "sectionName": section_name
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)

@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_contest_by_id(request, contest_id):
    try:
        result = collection.delete_one({'contestId': contest_id})
        if result.deleted_count > 0:
            return Response({'message': 'Contest deleted successfully'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Contest not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@csrf_exempt
def close_session(request, contest_id):
    if request.method == "POST":
        try:
            # Find the document with the given contest ID and update it
            result = collection.update_one(
                {"contestId": contest_id},  # Find document with this contestId
                {"$set": {"Overall_Status": "closed"}}  # Set session to "closed"
            )

            if result.matched_count > 0:  # Check if any document was updated
                return JsonResponse({"message": "Session closed successfully."}, status=200)
            else:
                return JsonResponse({"message": "Contest ID not found."}, status=404)

        except Exception as e:
            print(f"Error while updating MongoDB: {e}")
            return JsonResponse({"message": "Internal server error."}, status=500)

    return JsonResponse({"message": "Invalid request method."}, status=405)