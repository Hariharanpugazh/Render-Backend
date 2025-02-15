from django.http import JsonResponse
from pymongo import MongoClient
from bson import ObjectId

def download_contest_data(request, contest_id):
    # Connect to MongoDB
    client = MongoClient('mongodb+srv://krish:krish@assessment.ar5zh.mongodb.net/')
    db = client['test_portal_db']
    questions_collection = db['MCQ_Assessment_report']
    students_collection = db['students']

    # Fetch data for the specific contest from MongoDB
    data = list(questions_collection.find({'contest_id': contest_id}))

    if not data:
        return JsonResponse({"error": "No data found for the specified contest ID."}, status=404)

    # Extract student data
    students = data[0].get('students', [])

    if not students:
        return JsonResponse({"error": "No student data found for the specified contest ID."}, status=404)

    # Extract student IDs
    student_ids = [ObjectId(student['student_id']) for student in students]

    # Fetch corresponding student data from the 'students' collection
    student_data = list(students_collection.find({'_id': {'$in': student_ids}}))

    # Create a dictionary to map student IDs to their data
    student_data_map = {str(student['_id']): student for student in student_data}

    # Calculate the average percentage
    total_percentage = sum(student['percentage'] for student in students)
    average_percentage = total_percentage / len(students)

    # Prepare the JSON response
    response_data = {
        "average_percentage": average_percentage,
        "students": [
            {
                "student_id": student['student_id'],
                "percentage": student['percentage'],
                "name": student_data_map.get(student['student_id'], {}).get('name', ''),
                "email": student_data_map.get(student['student_id'], {}).get('email', ''),
                "collegename": student_data_map.get(student['student_id'], {}).get('collegename', ''),
                "dept": student_data_map.get(student['student_id'], {}).get('dept', ''),
                "regno": student_data_map.get(student['student_id'], {}).get('regno', ''),
                "year": student_data_map.get(student['student_id'], {}).get('year', '')
            }
            for student in students
        ]
    }

    return JsonResponse(response_data)
