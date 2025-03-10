from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
from bson import ObjectId
import json
import jwt
from rest_framework.exceptions import AuthenticationFailed
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Add these constants at the top of your file
SECRET_KEY = "Rahul"
JWT_SECRET = 'test'
JWT_ALGORITHM = 'HS256'

@csrf_exempt
def student_profile(request):
    client = MongoClient('mongodb+srv://krish:krish@assessment.ar5zh.mongodb.net/')
    db = client['test_portal_db']
    students_collection = db['students']
    staff_collection = db['staff']

    try:
        # Extract and decode JWT token
        jwt_token = request.COOKIES.get('jwt')
        if not jwt_token:
            raise AuthenticationFailed('Authentication credentials were not provided.')

        try:
            decoded_token = jwt.decode(jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired.')
        except jwt.InvalidTokenError:
            raise AuthenticationFailed('Invalid token.')

        # Get staff_id from decoded token
        staff_id = decoded_token.get('staff_user')
        if not staff_id:
            raise AuthenticationFailed('Invalid token payload.')

        # Get staff details from staff collection
        staff_details = staff_collection.find_one({'_id': ObjectId(staff_id)})
        if not staff_details:
            return JsonResponse({'error': 'Staff not found'}, status=404)

        staff_role = staff_details.get('role', '').strip()
        staff_college = staff_details.get('collegename', '').strip()
        
        # Handle both string and array formats for department
        staff_department_raw = staff_details.get('department', '')
        if isinstance(staff_department_raw, list):
            staff_department = [dept.strip().lower() for dept in staff_department_raw if dept]
            logger.info(f"Staff has multiple departments: {staff_department}")
        else:
            staff_department = staff_department_raw.strip().lower()
            logger.info(f"Staff has single department: {staff_department}")

        logger.info(f"Staff Role: {staff_role}")
        logger.info(f"Staff College: {staff_college}")
        logger.info(f"Staff Department: {staff_department}")

        if request.method == 'GET':
            # Build query based on role
            if staff_role == 'Admin':
                # Admin can see all students in the system
                query = {}
                logger.info("Admin access: retrieving all students")
            elif staff_role == 'Principal':
                # Principal can see all students from their college
                query = {
                    'collegename': {'$regex': f'^{staff_college}$', '$options': 'i'}
                }
            else:
                # Construct query for HOD or Staff
                if isinstance(staff_department, list):
                    # HOD with multiple departments
                    or_conditions = []
                    for dept in staff_department:
                        or_conditions.append({
                            'dept': {'$regex': f'^{dept}$', '$options': 'i'},
                            'collegename': {'$regex': f'^{staff_college}$', '$options': 'i'}
                        })
                    query = {'$or': or_conditions}
                    logger.info(f"HOD access with multiple departments: {staff_department}")
                else:
                    # Single department staff
                    query = {
                        'dept': {'$regex': f'^{staff_department}$', '$options': 'i'},
                        'collegename': {'$regex': f'^{staff_college}$', '$options': 'i'}
                    }
                    logger.info(f"Staff access for department: {staff_department}")

            logger.info(f"MongoDB Query: {query}")

            # Get students matching the query
            students = list(students_collection.find(query, {'_id': 0}))

            logger.info(f"Total students found: {len(students)}")
            logger.debug(f"First few students: {students[:2] if students else []}")

            return JsonResponse({
                'students': students,
                'staffDepartment': staff_department,  # This is already handled correctly as array or string
                'staffCollege': staff_college,
                'staffRole': staff_role,
                'status': 'success',
                'query': str(query)
            }, safe=False)

        elif request.method == 'POST':
            try:
                data = json.loads(request.body)
                
                # For Admin, use the provided data directly
                if staff_role != 'Admin':
                    # For non-admins, enforce their department and college
                    
                    # If staff_department is a list, take the first element
                    if isinstance(staff_department, list):
                        dept = staff_department[0] if staff_department else ''
                    else:
                        dept = staff_department
                    
                    data.update({
                        'dept': dept,
                        'collegename': staff_college
                    })
                    
                filter_query = {"regno": data["regno"]}
                students_collection.update_one(filter_query, {"$set": data}, upsert=True)
                return JsonResponse({"message": "Student details updated successfully"}, status=201)
            except Exception as e:
                logger.error(f"Error in POST request: {str(e)}")
                return JsonResponse({"error": str(e)}, status=400)

    except AuthenticationFailed as auth_failed:
        logger.error(f"Authentication failed: {str(auth_failed)}")
        return JsonResponse({"error": str(auth_failed)}, status=401)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)
    finally:
        client.close()