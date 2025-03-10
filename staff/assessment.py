import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.exceptions import AuthenticationFailed  # Import this exception
from rest_framework import status  # Import status codes
from rest_framework.response import Response #import Response
from .utils import *
import logging
import jwt
from bson import errors

# MongoDB connection
client = MongoClient('mongodb+srv://krish:krish@assessment.ar5zh.mongodb.net/')
db = client['test_portal_db']
coding_assessments_collection = db['coding_assessments']
staff_collection = db['staff']

JWT_SECRET = 'test'
JWT_ALGORITHM = "HS256"

# Helper function to convert string to datetime object (for registration dates)
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)


from datetime import datetime
def str_to_datetime(date_str):
    if not date_str or date_str == 'T':
        # If the date string is empty or just contains 'T', return None or raise an error
        raise ValueError(f"Invalid datetime format: {date_str}")

    try:
        # Try parsing the full datetime format (with seconds)
        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        try:
            # If there's no seconds, try parsing without seconds
            return datetime.strptime(date_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            # If both parsing methods fail, raise an error
            raise ValueError(f"Invalid datetime format: {date_str}")# Create Assessment (POST method)
        
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])  # Ensure authentication (optional in your context)
def create_assessment(request):
    """
    Endpoint to create a new assessment.
    """
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

        # 2. Validate staff existence in MongoDB
        try:
            staff = staff_collection.find_one({"_id": ObjectId(staff_id)})
        except errors.InvalidId:
            logger.error("Invalid staff_id format in token")
            raise AuthenticationFailed("Invalid token payload.")

        if not staff:
            logger.error("Staff not found with ID: %s", staff_id)
            return JsonResponse({"error": "Staff not found"}, status=404)

        # 3. Parse and validate the request body
        data = request.data  # Using DRF's parsed data
        logger.info("Received Payload: %s", data)

        assessment_overview = data.get("assessmentOverview", {})
        test_configuration = data.get("testConfiguration", {})

        # Required Fields Validation
        required_fields = ["name", "guidelines", "registrationStart", "registrationEnd"]
        for field in required_fields:
            if not assessment_overview.get(field):
                logger.warning("Missing required field: %s", field)
                return JsonResponse({"error": f"{field} is required in assessmentOverview"}, status=400)

        # Validate date format
        try:
            registration_start = datetime.fromisoformat(assessment_overview["registrationStart"])
            registration_end = datetime.fromisoformat(assessment_overview["registrationEnd"])
        except ValueError:
            logger.error("Invalid date format for registrationStart or registrationEnd")
            return JsonResponse({"error": "Invalid date format. Use ISO format for dates."}, status=400)

        # 4. Prepare the assessment document
        contest_id = str(ObjectId())  # Generate a unique contest ID
        assessment_document = {
            "contestId": contest_id,
            "assessmentOverview": {
                "name": assessment_overview["name"],
                "description": assessment_overview.get("description", ""),
                "registrationStart": registration_start,
                "registrationEnd": registration_end,
                "guidelines": assessment_overview["guidelines"],
            },
            "testConfiguration": {
                "questions": test_configuration.get("questions", ""),
                "duration": test_configuration.get("duration", ""),
                "fullScreenMode": test_configuration.get("fullScreenMode", False),
                "faceDetection": test_configuration.get("faceDetection", False),
                "deviceRestriction": test_configuration.get("deviceRestriction", False),
                "noiseDetection": test_configuration.get("noiseDetection", False),
                "passPercentage": test_configuration.get("passPercentage", ""),
                "resultVisibility": test_configuration.get("resultVisibility", ""),
            },
            "staffId": staff_id,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow(),
        }

        # 5. Insert the document into MongoDB
        result = coding_assessments_collection.insert_one(assessment_document)
        logger.info("Assessment document inserted: %s", result.inserted_id)

        # 6. Return success response
        return JsonResponse(
            {
                "message": "Assessment created successfully!",
                "assessmentId": contest_id,
            },
            status=201,
        )

    except AuthenticationFailed as auth_error:
        logger.warning("Authentication failed: %s", str(auth_error))
        return JsonResponse({"error": str(auth_error)}, status=401)
    except Exception as e:
        logger.exception("Unexpected error occurred")
        return JsonResponse({"error": "An unexpected error occurred"}, status=500)

# @api_view(['PUT'])
# @authentication_classes([])
# @permission_classes([AllowAny])
# def update_assessment(request, contest_id):
#     """
#     Endpoint to update an existing assessment.
#     """
#     try:
#         # 1. Extract and decode the JWT token from cookies
#         jwt_token = request.COOKIES.get("jwt")
#         print(f"JWT Token: {jwt_token}")
#         if not jwt_token:
#             logger.warning("JWT Token missing in cookies")
#             raise AuthenticationFailed("Authentication credentials were not provided.")

#         try:
#             decoded_token = jwt.decode(jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
#             logger.info("Decoded JWT Token: %s", decoded_token)
#         except jwt.ExpiredSignatureError:
#             logger.error("Expired JWT Token")
#             raise AuthenticationFailed("Access token has expired. Please log in again.")
#         except jwt.InvalidTokenError:
#             logger.error("Invalid JWT Token")
#             raise AuthenticationFailed("Invalid token. Please log in again.")

#         staff_id = decoded_token.get("staff_user")
#         if not staff_id:
#             logger.warning("Invalid payload: 'staff_user' missing")
#             raise AuthenticationFailed("Invalid token payload.")

#         # 2. Validate staff existence in MongoDB
#         try:
#             staff = staff_collection.find_one({"_id": ObjectId(staff_id)})
#         except errors.InvalidId:
#             logger.error("Invalid staff_id format in token")
#             raise AuthenticationFailed("Invalid token payload.")

#         if not staff:
#             logger.error("Staff not found with ID: %s", staff_id)
#             return JsonResponse({"error": "Staff not found"}, status=404)

#         # 3. Retrieve the assessment from MongoDB
#         assessment = coding_assessments_collection.find_one({"contestId": contest_id})
#         if not assessment:
#             logger.warning("Assessment not found with contestId: %s", contest_id)
#             return JsonResponse({"error": "Assessment not found"}, status=404)

#         # 4. Parse the request data
#         data = request.data
#         logger.info(f"Update Payload: {data}")

#         assessment_overview = data.get("assessmentOverview", {})
#         test_configuration = data.get("testConfiguration", {})

#         # 5. Validate date format
#         try:
#             registration_start = str_to_datetime(assessment_overview.get("registrationStart"))
#             registration_end = str_to_datetime(assessment_overview.get("registrationEnd"))
#         except ValueError as e:
#             logger.error("Invalid date format for registrationStart or registrationEnd: %s", str(e))
#             return JsonResponse({"error": "Invalid date format. Use ISO format for dates."}, status=400)

#         # 6. Update the assessment document
#         updated_fields = {
#             "assessmentOverview": {
#                 "name": assessment_overview.get("name", assessment["assessmentOverview"]["name"]),
#                 "description": assessment_overview.get("description", assessment["assessmentOverview"]["description"]),
#                 "registrationStart": registration_start if registration_start else assessment["assessmentOverview"]["registrationStart"],
#                 "registrationEnd": registration_end if registration_end else assessment["assessmentOverview"]["registrationEnd"],
#                 "guidelines": assessment_overview.get("guidelines", assessment["assessmentOverview"]["guidelines"]),
#                 "sectionDetails": assessment_overview.get("sectionDetails", assessment["assessmentOverview"].get("sectionDetails", "No")),  # Keep sectionDetails
#             },
#             "testConfiguration": {
#                 "questions": test_configuration.get("questions", assessment["testConfiguration"]["questions"]),
#                 "duration": test_configuration.get("duration", assessment["testConfiguration"]["duration"]),
#                 "fullScreenMode": test_configuration.get("fullScreenMode", assessment["testConfiguration"]["fullScreenMode"]),
#                 "faceDetection": test_configuration.get("faceDetection", assessment["testConfiguration"]["faceDetection"]),
#                 "deviceRestriction": test_configuration.get("deviceRestriction", assessment["testConfiguration"]["deviceRestriction"]),
#                 "noiseDetection": test_configuration.get("noiseDetection", assessment["testConfiguration"]["noiseDetection"]),
#                 "passPercentage": test_configuration.get("passPercentage", assessment["testConfiguration"]["passPercentage"]),
#                 "resultVisibility": test_configuration.get("resultVisibility", assessment["testConfiguration"]["resultVisibility"]),
#             },
#             "updatedAt": datetime.utcnow(),
#         }

#         # 7. Update the document in MongoDB
#         result = coding_assessments_collection.update_one(
#             {"contestId": contest_id},
#             {"$set": updated_fields}
#         )

#         if result.modified_count == 0:
#             logger.warning("No assessment modified with contestId: %s", contest_id)
#             return JsonResponse({"message": "No changes were applied"}, status=200)

#         logger.info("Assessment document updated: %s", contest_id)

#         # 8. Return success response
#         return JsonResponse({"message": "Assessment updated successfully!"}, status=200)

#     except AuthenticationFailed as auth_error:
#         logger.warning("Authentication failed: %s", str(auth_error))
#         return JsonResponse({"error": str(auth_error)}, status=401)
#     except Exception as e:
#         logger.exception("Unexpected error occurred")
#         return JsonResponse({"error": str(e)}, status=500)  # Include the actual error message for debugging