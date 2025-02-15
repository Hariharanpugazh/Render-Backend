from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.hashers import check_password, make_password
from rest_framework.exceptions import AuthenticationFailed
from bson import ObjectId
from datetime import datetime
import logging
import json
from rest_framework.views import csrf_exempt
from .utils import *
from django.core.cache import cache
from django.http import JsonResponse
from rest_framework import status
from datetime import datetime, timedelta
import jwt
logger = logging.getLogger(__name__)



# Secret and algorithm for signing the tokens
JWT_SECRET = 'test'
JWT_ALGORITHM = "HS256"

def generate_tokens_for_student(student_id, regno):
    """
    Generate a secure access token (JWT) for a user with a MongoDB ObjectId and regno.
    """
    access_payload = {
        'student_id': str(student_id),
        'regno': regno,  # Add regno to the token payload
        'exp': datetime.utcnow() + timedelta(minutes=600),  # Access token expiration
        'iat': datetime.utcnow(),
    }

    # Encode the token
    token = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    print(token)
    return {'jwt': token}



@api_view(["POST"])
@permission_classes([AllowAny])  # Allow unauthenticated access for login
def student_login(request):
    """
    Login view for students
    """ 
    try:
        data = request.data
        email = data.get("email")
        password = data.get("password")

        # Validate input
        if not email or not password:
            return Response({"error": "Email and password are required"}, status=400)

        # Fetch student user from MongoDB
        student_user = student_collection.find_one({"email": email})
        if not student_user:
            return Response({"error": "Invalid email or password"}, status=401)

        # Check password
        stored_password = student_user["password"]
        if check_password(password, stored_password):
            # Generate tokens with regno included
            tokens = generate_tokens_for_student(
                str(student_user["_id"]),
                student_user.get("regno")
            )


            # Create response and set secure cookie
            response = Response({
                "message": "Login successful",
                "tokens": tokens,
                "studentId": str(student_user["_id"]),
                "name": student_user["name"],
                "email": student_user["email"],
                "regno": student_user["regno"],
                "dept": student_user["dept"],
                "collegename": student_user["collegename"]
            })

            # Use secure=False for local development
            response.set_cookie(
                key='jwt',
                value=tokens['jwt'],
                httponly=True,
                samesite='None',
                secure=True,
                max_age=1 * 24 * 60 * 60
                # domain='http://localhost:8000/' # 1 day in seconds
            )
            print("JWT",tokens['jwt'])
            print("JWT2",response)
            return response

        return Response({"error": "Invalid email or password"}, status=401)

    except KeyError as e:
        logger.error(f"Missing key: {e}")
        return Response({"error": "Invalid data provided"}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return Response({"error": "An unexpected error occurred"}, status=500)

@api_view(["POST"])
@permission_classes([AllowAny])  # Allow signup without authentication
def student_signup(request):
    """
    Signup view for students
    """
    try:
        # Extract data from request
        data = request.data
        student_user = {
            "name": data.get("name"),
            "email": data.get("email"),
            "password": make_password(data.get("password")),
            "collegename": data.get("collegename"),
            "dept": data.get("dept"),
            "regno": data.get("regno"),
            "year": data.get("year"),  # Add year field
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        # Validate required fields
        required_fields = ["name", "email", "password", "dept", "collegename", "regno", "year"]
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return Response(
                {"error": f"Missing required fields: {', '.join(missing_fields)}"},
                status=400,
            )

        # Validate year field
        valid_years = ["I", "II", "III", "IV"]
        if student_user["year"] not in valid_years:
            return Response({"error": "Invalid year. Must be one of I, II, III, IV."}, status=400)

        # Check if email already exists
        if student_collection.find_one({"email": student_user["email"]}):
            return Response({"error": "Email already exists"}, status=400)

        # Check if regno already exists
        if student_collection.find_one({"regno": student_user["regno"]}):
            return Response({"error": "Registration number already exists"}, status=400)

        # Insert student profile into MongoDB
        student_collection.insert_one(student_user)
        return Response({"message": "Signup successful"}, status=201)

    except Exception as e:
        logger.error(f"Error during student signup: {e}")
        return Response(
            {"error": "Something went wrong. Please try again later."}, status=500
        )


@api_view(["GET"])
@permission_classes([AllowAny])  # Allow  without authentication
def student_profile(request):
    """
    API to fetch the profile details of the logged-in student.
    """
    try:
        # Retrieve the JWT token from cookies
        jwt_token = request.COOKIES.get("jwt")
        print(f"JWT Token: {jwt_token}")
        if not jwt_token:
            raise AuthenticationFailed("Authentication credentials were not provided.")

        # Decode the JWT token
        try: 
            decoded_token = jwt.decode(jwt_token, 'test', algorithms=["HS256"])
            # print(f"Decoded Token: {decoded_token}")
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Access token has expired. Please log in again.")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid token. Please log in again.")

        # Extract student ID from the decoded token
        student_id = decoded_token.get("student_id")

        if not student_id:
            raise AuthenticationFailed("Invalid token payload.")

        # Fetch student details from the database
        student = student_collection.find_one({"_id": ObjectId(student_id)})
        if not student:
            return Response({"error": "Student not found"}, status=404)

        # Prepare the response data
        response_data = {
            "studentId": str(student["_id"]),
            "name": student.get("name"),
            "email": student.get("email"),
            "regno": student.get("regno"),
            "dept": student.get("dept"),
            "collegename": student.get("collegename"),
        }

        return Response(response_data, status=200)

    except AuthenticationFailed as auth_error:
        return Response({"error": str(auth_error)}, status=401)
    except Exception as e:
        print(f"Unexpected error in student_profile: {e}")
        return Response({"error": "An unexpected error occurred"}, status=500)

@api_view(["GET"])
@permission_classes([AllowAny])  # Allow without authentication
def get_students(request):
    cache.clear()  # Clear cache here
    try:
        # Fetch students from the database, including the "year" field
        students = list(student_collection.find(
            {}, 
            {"_id": 1, "name": 1, "regno": 1, "dept": 1, "collegename": 1, "year": 1, "email":1}  # Include "year" field
        ))
        
        # Rename _id to studentId and convert to string
        for student in students:
            student["studentId"] = str(student["_id"])  # Convert ObjectId to string
            del student["_id"]  # Remove original _id to avoid confusion
        
        return Response(students, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(["GET"])
@permission_classes([AllowAny])  # Allow unauthenticated access for testing
def get_tests_for_student(request):
    """
    API to fetch tests assigned to a student based on regno from JWT,
    including the entire document.
    """
    try:
        # Retrieve the JWT token from cookies
        jwt_token = request.COOKIES.get("jwt")
        if not jwt_token:
            raise AuthenticationFailed("Authentication credentials were not provided.")

        # Decode the JWT token
        try:
            decoded_token = jwt.decode(jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Access token has expired. Please log in again.")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid token. Please log in again.")

        # Extract regno from the decoded token
        regno = decoded_token.get("regno")
        if not regno:
            return JsonResponse({"error": "Invalid token payload."}, status=401)

        # Fetch contests where the student is visible in visible_to
        contests = list(coding_assessments_collection.find(
            {"visible_to": regno}  # Filter only on 'visible_to'
        ))

        if not contests:
            return JsonResponse([], safe=False, status=200)  # Return an empty list if no contests are found

        # Convert ObjectId to string for JSON compatibility and format response
        formatted_response = [
            {
                **contest,  # Spread the entire contest object
                "_id": str(contest["_id"]),  # Convert _id (ObjectId) to string
            }
            for contest in contests
        ]

        return JsonResponse(formatted_response, safe=False, status=200)

    except AuthenticationFailed as auth_error:
        return JsonResponse({"error": str(auth_error)}, status=401)
    except Exception as e:
        print("Error fetching tests for student:", str(e))
        return JsonResponse({"error": "Failed to fetch tests"}, status=500)

@api_view(["GET"])
@permission_classes([AllowAny])  # Allow unauthenticated access for testing
def get_tests_for_student(request):
    """
    API to fetch tests assigned to a student based on regno from JWT,
    including the entire document.
    """
    try:
        # Retrieve the JWT token from cookies
        jwt_token = request.COOKIES.get("jwt")
        if not jwt_token:
            raise AuthenticationFailed("Authentication credentials were not provided.")

        # Decode the JWT token
        try:
            decoded_token = jwt.decode(jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Access token has expired. Please log in again.")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid token. Please log in again.")

        # Extract regno from the decoded token
        regno = decoded_token.get("regno")
        if not regno:
            return JsonResponse({"error": "Invalid token payload."}, status=401)

        # Fetch contests where the student is visible in visible_to
        contests = list(coding_assessments_collection.find(
            {"visible_to": regno}  # Filter only on 'visible_to'
        ))

        if not contests:
            return JsonResponse([], safe=False, status=200)  # Return an empty list if no contests are found

        # Convert ObjectId to string for JSON compatibility and format response
        formatted_response = [
            {
                **contest,  # Spread the entire contest object
                "_id": str(contest["_id"]),  # Convert _id (ObjectId) to string
            }
            for contest in contests
        ]

        return JsonResponse(formatted_response, safe=False, status=200)

    except AuthenticationFailed as auth_error:
        return JsonResponse({"error": str(auth_error)}, status=401)
    except Exception as e:
        print("Error fetching tests for student:", str(e))
        return JsonResponse({"error": "Failed to fetch tests"}, status=500)



@api_view(["GET"])
@permission_classes([AllowAny])  # Allow unauthenticated access for testing
def get_mcq_tests_for_student(request):
    """
    API to fetch MCQ tests assigned to a student based on regno from JWT,
    including the entire document.
    """
    try:
        # Retrieve the JWT token from cookies
        jwt_token = request.COOKIES.get("jwt")
        if not jwt_token:
            raise AuthenticationFailed("Authentication credentials were not provided.")

        # Decode the JWT token
        try:
            decoded_token = jwt.decode(jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Access token has expired. Please log in again.")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid token. Please log in again.")

        # Extract regno from the decoded token
        regno = decoded_token.get("regno")
        if not regno:
            return JsonResponse({"error": "Invalid token payload."}, status=401)

        # Optimize: Add projection to fetch only needed fields and exclude unnecessary ones
        mcq_tests = list(mcq_assessments_collection.find(
            {"visible_to": regno},
            {"questions": 0, "correctAnswer": 0 }
        ))

        if not mcq_tests:
            return JsonResponse([], safe=False, status=200)

        # Optimize: Use list comprehension for faster processing
        formatted_response = [{
            **test,
            "_id": test['contestId'],
            "assessment_type": "mcq",
            "sections": bool(test.get('sections'))
        } for test in mcq_tests]

        return JsonResponse(formatted_response, safe=False, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["GET"])
@permission_classes([AllowAny])  # Allow unauthenticated access for testing
def get_coding_reports_for_student(request):
    """
    API to fetch coding reports for a student based on student_id from JWT.
    """
    try:
        # Retrieve the JWT token from cookies
        jwt_token = request.COOKIES.get("jwt")
        if not jwt_token:
            raise AuthenticationFailed("Authentication credentials were not provided.")

        # Decode the JWT token
        try:
            decoded_token = jwt.decode(jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Access token has expired. Please log in again.")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid token. Please log in again.")

        # Extract student_id from the decoded token
        student_id = decoded_token.get("student_id")
        if not student_id:
            return JsonResponse({"error": "Invalid token payload."}, status=401)

        # Fetch coding reports where the student's student_id matches
        coding_reports = list(coding_report_collection.find({}))

        if not coding_reports:
            return JsonResponse([], safe=False, status=200)  # Return an empty list if no reports are found

        # Convert ObjectId to string for JSON compatibility and format response
        formatted_response = []
        for report in coding_reports:
            for student in report["students"]:
                if student["student_id"] == student_id:
                    formatted_response.append({
                        "contest_id": report["contest_id"],
                        "student_id": student["student_id"],
                        "status": student["status"]
                    })

        return JsonResponse(formatted_response, safe=False, status=200)

    except AuthenticationFailed as auth_error:
        return JsonResponse({"error": str(auth_error)}, status=401)
    except Exception as e:
        print("Error fetching coding reports for student:", str(e))
        return JsonResponse({"error": "Failed to fetch coding reports"}, status=500)

@api_view(["GET"])
@permission_classes([AllowAny])
def get_mcq_reports_for_student(request):
    """
    API to fetch MCQ reports for a student based on student_id from JWT.
    """
    try:
        jwt_token = request.COOKIES.get("jwt")
        if not jwt_token:
            raise AuthenticationFailed("Authentication credentials were not provided.")

        try:
            decoded_token = jwt.decode(jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Access token has expired. Please log in again.")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Invalid token. Please log in again.")

        student_id = decoded_token.get("student_id")
        if not student_id:
            return JsonResponse({"error": "Invalid token payload."}, status=401)

        # Optimize: Use aggregation pipeline for better performance
        pipeline = [
            {
                "$match": {
                    "students.student_id": student_id
                }
            },
            {
                "$project": {
                    "contest_id": 1,
                    "students": {
                        "$filter": {
                            "input": "$students",
                            "as": "student",
                            "cond": {"$eq": ["$$student.student_id", student_id]}
                        }
                    }
                }
            }
        ]
        
        coding_reports = list(mcq_assessments_report_collection.aggregate(pipeline))
        
        if not coding_reports:
            return JsonResponse([], safe=False, status=200)

        formatted_response = []
        for report in coding_reports:
            for student in report["students"]:
                formatted_response.append({
                    "contest_id": report["contest_id"],
                    "student_id": student["student_id"],
                    "status": student["status"]
                })


        return JsonResponse(formatted_response, safe=False, status=200)

    except AuthenticationFailed as auth_error:
        return JsonResponse({"error": str(auth_error)}, status=401)
    except Exception as e:
        print("Error fetching coding reports for student:", str(e))
        return JsonResponse({"error": "Failed to fetch coding reports"}, status=500)

@csrf_exempt
def check_publish_status(request):
    """
    API to check whether the results for a specific test or contest have been published.
    """
    try:
        if request.method != 'POST':
            return JsonResponse({"error": "Invalid request method"}, status=405)

        data = json.loads(request.body)
        test_ids = data.get('testIds', [])

        if not test_ids:
            return JsonResponse({}, status=200)


        # Optimize: Use bulk operations for multiple IDs
        mcq_reports = mcq_assessments_report_collection.find(
            {"contest_id": {"$in": test_ids}},
            {"contest_id": 1, "ispublish": 1}
        )
        coding_reports = coding_report_collection.find(
            {"contest_id": {"$in": test_ids}},
            {"contest_id": 1, "ispublish": 1}
        )

        # Combine results from both collections
        publish_status = {}
        for report in list(mcq_reports) + list(coding_reports):
            contest_id = report["contest_id"]
            if contest_id not in publish_status:  # Only take first occurrence
                publish_status[contest_id] = report.get("ispublish", False)

        # Fill in missing test_ids with False
        for test_id in test_ids:
            if test_id not in publish_status:
                publish_status[test_id] = False


        return JsonResponse(publish_status, status=200)

    except Exception as e:
        return JsonResponse({"error": f"Failed to check publish status: {str(e)}"}, status=500)
    
@csrf_exempt
def student_section_details(request, contest_id):
    if request.method == "GET":
        # Fetch contest details by contestId
        contest = mcq_assessments_collection.find_one(
            {"contestId": contest_id},
            {"sections": 1, "assessmentOverview.guidelines": 1, "_id": 0}
        )

        if not contest:
            return JsonResponse({"error": "Contest not found"}, status=404)

        sections = contest.get("sections", [])
        guidelines = contest.get("assessmentOverview", {}).get("guidelines", "")

        # Calculate total duration
        total_duration = sum(section.get("sectionDuration", 0) for section in sections)

        # Format the response with section name, number of questions, and duration
        section_data = [
            {
                "name": section["sectionName"],
                "numQuestions": section["numQuestions"],
                "duration": section.get("sectionDuration", 0),
            }
            for section in sections
        ]

        return JsonResponse({
            "sections": section_data,
            "guidelines": guidelines,
            "totalDuration": total_duration  # Include total duration in response
        }, status=200)

    return JsonResponse({"error": "Invalid request method"}, status=400)