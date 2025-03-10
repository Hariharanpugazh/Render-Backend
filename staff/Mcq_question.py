import csv
from pymongo import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
import json
import uuid
from bson import ObjectId
import re
import logging

# MongoDB connection
client = MongoClient('mongodb+srv://krish:krish@assessment.ar5zh.mongodb.net/')
db = client['test_portal_db']

questions_collection = db['MCQ_Questions_Library']
tests_collection = db['MCQ_Tests_Library']

logger = logging.getLogger(__name__)

@csrf_exempt
def bulk_upload(request):
    if request.method == "POST" and request.FILES.get("file"):
        # Save the uploaded file temporarily
        file = request.FILES["file"]
        fs = FileSystemStorage(location="uploads/")
        filename = fs.save(file.name, file)
        file_path = fs.path(filename)

        try:
            # Process the CSV file with UTF-8-BOM encoding
            with open(file_path, "r", encoding="utf-8-sig") as csv_file:
                csv_reader = csv.DictReader(csv_file)
                questions = []
                for row in csv_reader:
                    # Clean up potential BOM issues
                    first_key = list(row.keys())[0]
                    question = row.get(first_key, "").strip() if '\ufeff' in first_key else row.get("question", "").strip()
                    options = [row.get(f"option{i}", "").strip() for i in range(1, 7) if row.get(f"option{i}")]
                    correctAnswer = row.get("correctAnswer", "").strip()  # Rename to correctAnswer
                    level = row.get("Level", "").strip().lower()  # Fetch level from file
                    tags = row.get("tags", "").strip()  # Fetch tags as a string
                    blooms = row.get("blooms", "").strip()  # Fetch blooms from file

                    # If level is missing or invalid, use 'general' as the default level
                    if not level or level not in {"easy", "medium", "hard"}:
                        level = "general"

                    # Ensure there are at least 2 options and at most 6 options
                    if len(options) < 2 or len(options) > 6:
                        print(f"Skipping invalid row due to incorrect number of options: {row}")
                        continue

                    # Skip rows with missing critical information
                    if not all([question, correctAnswer]):
                        print(f"Skipping invalid row: {row}")
                        continue

                    # Validate answer is one of the options
                    if correctAnswer not in options:
                        print(f"Invalid answer for question: {question}")
                        continue

                    # Prepare question data with the level from the CSV
                    question_data = {
                        "question_id": str(uuid.uuid4()),
                        "question": question,
                        "options": options,
                        "correctAnswer": correctAnswer,  # Use correctAnswer
                        "level": level,  # Use level from CSV or default to 'general'
                        "tags": tags,  # Store tags as a string
                        "blooms": blooms  # Add blooms field
                    }
                    questions.append(question_data)

                # Insert all questions into MongoDB
                if questions:
                    # Debug: Print the prepared data
                    print(f"Prepared questions for insertion: {questions}")

                    # Insert questions into MongoDB
                    result = questions_collection.insert_many(questions)

                    # Debug: Check the result of insertion
                    print(f"Inserted {len(result.inserted_ids)} questions with levels: {[q['level'] for q in questions]}")
                    return JsonResponse({
                        "message": f"File uploaded and {len(result.inserted_ids)} questions stored successfully!",
                        "inserted_count": len(result.inserted_ids)
                    }, status=200)
                else:
                    return JsonResponse({"error": "No valid questions found in the CSV file."}, status=400)

        except csv.Error as csv_error:
            print(f"CSV Error: {csv_error}")
            return JsonResponse({"error": f"CSV parsing error: {str(csv_error)}"}, status=400)
        except Exception as e:
            print(f"Unexpected error: {e}")
            return JsonResponse({"error": str(e)}, status=400)
        finally:
            # Clean up the uploaded file
            fs.delete(filename)

    return JsonResponse({"error": "Invalid request. Please upload a file."}, status=400)

@csrf_exempt
def upload_single_question(request):
    if request.method == "POST":
        try:
            # Parse JSON data from the request body
            data = json.loads(request.body)

            # Extract question details
            question = data.get("question", "").strip()
            option1 = data.get("option1", "").strip()
            option2 = data.get("option2", "").strip()
            option3 = data.get("option3", "").strip()
            option4 = data.get("option4", "").strip()
            option5 = data.get("option5", "").strip()  # Added option5
            option6 = data.get("option6", "").strip()  # Added option6
            correctAnswer = data.get("answer", "").strip()  # Rename to correctAnswer
            level = data.get("level", "general").strip()  # Fix inconsistent key
            tags = data.get("tags", [])  # Default to an empty list if no tags provided
            blooms = data.get("blooms", "").strip()  # Extract blooms level

            # Validate input
            options = [option1, option2, option3, option4, option5, option6]
            non_empty_options = [option for option in options if option]

            if not all([question, correctAnswer]) or len(non_empty_options) < 2:
                return JsonResponse({
                    "error": "Missing required fields. Please provide a question, at least two options, and a correct answer."
                }, status=400)

            # Validate answer is one of the options
            if correctAnswer not in non_empty_options:
                return JsonResponse({
                    "error": "Invalid answer. The answer must be one of the provided options."
                }, status=400)

            # Prepare question data
            question_data = {
                "question_id": str(uuid.uuid4()),
                "question": question,
                "options": non_empty_options,
                "correctAnswer": correctAnswer,  # Use correctAnswer
                "level": level,
                "tags": tags,
                "blooms": blooms  # Add blooms level
            }

            # Insert the question into MongoDB
            result = questions_collection.insert_one(question_data)

            return JsonResponse({
                "message": "Question uploaded successfully!",
                "question_id": str(result.inserted_id)
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({
                "error": "Invalid JSON format. Please send a valid JSON payload."
            }, status=400)
        except Exception as e:
            return JsonResponse({
                "error": f"An unexpected error occurred: {str(e)}"
            }, status=500)

    return JsonResponse({
        "error": "Only POST requests are allowed."
    }, status=405)


def fetch_all_questions(request):
    try:
        # Get query parameters for filtering and searching
        level = request.GET.get('level', '').strip()
        tags = request.GET.getlist('tags')  # Supports multiple tags as a list
        search = request.GET.get('search', '').strip()

        # Build the MongoDB query
        query = {}
        if level:
            query['level'] = level
        if tags:
            query['tags'] = {'$all': tags}  # Matches all specified tags
        if search:
            query['$or'] = [
                {'question': {'$regex': re.escape(search), '$options': 'i'}},  # Case-insensitive search in question
                {'tags': {'$regex': re.escape(search), '$options': 'i'}}  # Case-insensitive search in tags
            ]

        # Fetch filtered data from MongoDB
        questions = list(questions_collection.find(query, {'_id': 0}))  # Exclude MongoDB's _id field

        return JsonResponse({"questions": questions}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def update_question(request, question_id):
    """
    Update an existing question in the database using a PUT request.
    Allows between 2 and 4 options.
    """
    if request.method == "PUT":
        try:
            # Parse JSON payload
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError as e:
                return JsonResponse({"error": f"Invalid JSON payload: {str(e)}"}, status=400)

            # Extract and clean fields
            question = data.get("question", "").strip()
            options = data.get("options", [])
            correctAnswer = data.get("correctAnswer", "").strip()
            level = data.get("level", "general").strip()
            tags = data.get("tags", [])

            # Input validation
            errors = []
            if not question:
                errors.append("Question text cannot be empty.")
            if len(options) < 2 or len(options) > 4:
                errors.append("Number of options must be between 2 and 4.")
            if len(set(options)) != len(options):
                errors.append("Options must be unique.")
            if not correctAnswer:
                errors.append("Answer cannot be empty.")
            if correctAnswer not in options:
                errors.append("Answer must be one of the provided options.")
            if errors:
                return JsonResponse({"error": errors}, status=400)

            # Build the update payload
            update_data = {
                "question": question,
                "options": options,
                "correctAnswer": correctAnswer,
                "level": level,
                "tags": tags,
            }

            # Execute the update query using question_id
            result = questions_collection.update_one(
                {"question_id": question_id}, {"$set": update_data}
            )

            # Check update status
            if result.matched_count == 0:
                return JsonResponse({"error": "Question not found"}, status=404)

            return JsonResponse({"message": "Question updated successfully"}, status=200)

        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Only PUT requests are allowed"}, status=405)

@csrf_exempt
def delete_question(request, question_id):
    if request.method == "DELETE":
        try:
            logger.debug(f"Attempting to delete question_id: {question_id}")
            result = questions_collection.delete_one({"question_id": question_id})
            logger.debug(f"Deleted count: {result.deleted_count}")

            if result.deleted_count == 0:
                return JsonResponse({"error": "Question not found"}, status=404)

            return JsonResponse({"message": "Question deleted successfully"}, status=200)

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Only DELETE requests are allowed"}, status=405)

@csrf_exempt
def create_test(request):
    if request.method == "POST":
        try:
            # Parse JSON data from the request body
            data = json.loads(request.body)

            # Extract test details
            test_name = data.get("test_name", "").strip()
            questions = data.get("questions", [])
            level = data.get("level", "general").strip()  # Add level field
            tags = data.get("tags", [])  # Add tags field
            category = data.get("category", "").strip()  # Add category field

            # Validate input
            if not test_name:
                return JsonResponse({"error": "Test name cannot be empty."}, status=400)
            if not questions:
                return JsonResponse({"error": "Questions list cannot be empty."}, status=400)

            # Prepare test data
            test_data = {
                "test_id": str(uuid.uuid4()),
                "test_name": test_name,
                "questions": questions,
                "level": level,  # Include level in test data
                "tags": tags,  # Include tags in test data
                "category": category  # Include category in test data
            }

            # Insert the test into MongoDB
            result = tests_collection.insert_one(test_data)

            return JsonResponse({
                "message": "Test created successfully!",
                "test_id": str(result.inserted_id)
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format. Please send a valid JSON payload."}, status=400)
        except Exception as e:
            return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)

    return JsonResponse({"error": "Only POST requests are allowed."}, status=405)



@csrf_exempt
def update_test(request, test_id):
    if request.method == "PUT":
        try:
            # Parse JSON payload
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError as e:
                return JsonResponse({"error": f"Invalid JSON payload: {str(e)}"}, status=400)

            # Extract and clean fields
            test_name = data.get("test_name", "").strip()
            level = data.get("level", "general").strip()
            tags = data.get("tags", [])
            category = data.get("category", "").strip()  # Add category field

            # Input validation
            errors = []
            if not test_name:
                errors.append("Test name cannot be empty.")
            if not category:
                errors.append("Category cannot be empty.")
            if errors:
                return JsonResponse({"error": errors}, status=400)

            # Build the update payload
            update_data = {
                "test_name": test_name,
                "level": level,
                "tags": tags,
                "category": category  # Include category in update data
            }

            # Execute the update query using test_id
            result = tests_collection.update_one(
                {"test_id": test_id}, {"$set": update_data}
            )

            # Check update status
            if result.matched_count == 0:
                return JsonResponse({"error": "Test not found"}, status=404)

            return JsonResponse({"message": "Test updated successfully"}, status=200)

        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Only PUT requests are allowed"}, status=405)


@csrf_exempt
def delete_test(request, test_id):
    if request.method == "DELETE":
        try:
            logger.debug(f"Attempting to delete test_id: {test_id}")
            result = tests_collection.delete_one({"test_id": test_id})
            logger.debug(f"Deleted count: {result.deleted_count}")

            if result.deleted_count == 0:
                return JsonResponse({"error": "Test not found"}, status=404)

            return JsonResponse({"message": "Test deleted successfully"}, status=200)

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Only DELETE requests are allowed"}, status=405)

@csrf_exempt
def fetch_all_tests(request):
    try:
        query = {}
        sort_field = None
        sort_order = 1  # Default to ascending order

        # Handle search query
        search_query = request.GET.get('search')
        if search_query:
            query['$or'] = [
                {'test_name': {'$regex': search_query, '$options': 'i'}},
                {'questions.question': {'$regex': search_query, '$options': 'i'}}
            ]

        # Handle filter by level
        filter_level = request.GET.get('level')
        if filter_level:
            query['level'] = filter_level

        # Handle sorting
        sort_param = request.GET.get('sort')
        if sort_param:
            if sort_param == 'name_asc':
                sort_field = 'test_name'
                sort_order = 1
            elif sort_param == 'name_desc':
                sort_field = 'test_name'
                sort_order = -1
            elif sort_param == 'level_asc':
                sort_field = 'level'
                sort_order = 1
            elif sort_param == 'level_desc':
                sort_field = 'level'
                sort_order = -1

        tests = list(tests_collection.find(query).sort(sort_field, sort_order) if sort_field else tests_collection.find(query))
        tests = [json.loads(json.dumps(test, default=str)) for test in tests]

        return JsonResponse({"tests": tests}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def fetch_questions_for_test(request):
    try:
        test_id = request.GET.get('test_id')
        if not test_id:
            return JsonResponse({"error": "test_id is required"}, status=400)

        query = {'test_id': test_id}
        sort_field = None
        sort_order = 1  # Default to ascending order

        # Handle search query
        search_query = request.GET.get('search')
        if search_query:
            query['questions.question'] = {'$regex': search_query, '$options': 'i'}

        # Handle filter by level
        filter_level = request.GET.get('level')
        if filter_level:
            query['questions.level'] = filter_level

        # Handle sorting
        sort_param = request.GET.get('sort')
        if sort_param:
            if sort_param == 'name_asc':
                sort_field = 'questions.question'
                sort_order = 1
            elif sort_param == 'name_desc':
                sort_field = 'questions.question'
                sort_order = -1
            elif sort_param == 'level_asc':
                sort_field = 'questions.level'
                sort_order = 1
            elif sort_param == 'level_desc':
                sort_field = 'questions.level'
                sort_order = -1

        test = tests_collection.find_one(query)
        if not test:
            return JsonResponse({"error": "Test not found"}, status=404)

        questions = test.get('questions', [])
        if search_query:
            questions = [q for q in questions if re.search(search_query, q['question'], re.IGNORECASE)]
        if filter_level:
            questions = [q for q in questions if q['level'] == filter_level]
        if sort_field:
            questions = sorted(questions, key=lambda q: q.get(sort_field.split('.')[1]), reverse=(sort_order == -1))

        if not questions:
            return JsonResponse({"message": "No questions found"}, status=404)

        return JsonResponse({"questions": questions}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def bulk_upload_test(request):
    if request.method == "POST":
        try:
            # Parse the JSON payload
            data = json.loads(request.body)

            # Extract necessary information
            test_id = data.get("test_id")
            test_name = str(data.get("test_name", "")).strip()
            level = str(data.get("level", "")).strip().lower()
            tags = data.get("tags", [])
            questions = data.get("questions", [])
            category = data.get("category", "").strip()  # Add category field

            # Validate level
            if level not in {"easy", "medium", "hard"}:
                level = "general"

            # Validate and process questions
            valid_questions = []
            for question_data in questions:
                question = str(question_data.get("question", "")).strip()
                options = [str(opt).strip() for opt in question_data.get("options", [])]
                correctAnswer = str(question_data.get("correctAnswer", "")).strip()
                question_level = str(question_data.get("level", "")).strip().lower()
                question_tags = question_data.get("tags", [])

                # If level is missing or invalid, use 'general' as the default level
                if not question_level or question_level not in {"easy", "medium", "hard"}:
                    question_level = "general"

                # Skip rows with missing critical information
                if not all([question, options, correctAnswer]):
                    print(f"Skipping invalid question: {question_data}")
                    continue

                # Validate answer is one of the options
                if correctAnswer not in options:
                    print(f"Invalid answer for question: {question}")
                    continue

                # Prepare question data
                valid_question = {
                    "question_id": str(uuid.uuid4()),
                    "question": question,
                    "options": options,
                    "correctAnswer": correctAnswer,
                    "level": question_level,
                    "tags": question_tags
                }
                valid_questions.append(valid_question)

            # Prepare the test document
            test_document = {
                "_id": ObjectId(),
                "test_id": test_id,
                "test_name": test_name,
                "level": level,
                "tags": tags,
                "questions": valid_questions,
                "category": category  # Include category in test data
            }

            # Insert or update the test document in the database
            result = tests_collection.update_one(
                {"test_id": test_id},
                {"$set": test_document},
                upsert=True
            )

            # Debug: Check the result of insertion
            if result.upserted_id or result.modified_count > 0:
                print(f"Inserted/Updated test {test_name} with {len(valid_questions)} questions")
                return JsonResponse({
                    "message": f"Questions added to test {test_name} successfully!",
                    "inserted_count": len(valid_questions)
                }, status=200)
            else:
                print(f"No documents matched the query for test {test_name}")
                return JsonResponse({"error": f"Test {test_name} not found."}, status=404)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)
        except Exception as e:
            print(f"Unexpected error: {e}")
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request. Please send a JSON payload."}, status=400)

@csrf_exempt
def delete_question_from_test(request, test_id, question_id):
    if request.method == "DELETE":
        try:
            logger.debug(f"Attempting to delete question_id: {question_id} from test_id: {test_id}")
            result = tests_collection.update_one(
                {"test_id": test_id},
                {"$pull": {"questions": {"question_id": question_id}}}
            )
            logger.debug(f"Modified count: {result.modified_count}")

            if result.modified_count == 0:
                return JsonResponse({"error": "Question not found in the test"}, status=404)

            return JsonResponse({"message": "Question deleted from the test successfully"}, status=200)

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Only DELETE requests are allowed"}, status=405)




@csrf_exempt
def bulk_upload_questions_to_test(request):
    if request.method == "POST":
        try:
            # Parse the JSON payload
            data = json.loads(request.body)

            # Extract necessary information
            test_id = data.get("test_id")
            questions = data.get("questions", [])

            if not test_id:
                return JsonResponse({"error": "test_id is required"}, status=400)

            # Validate and process questions
            valid_questions = []
            for question_data in questions:
                question = str(question_data.get("question", "")).strip()
                options = [
                    str(question_data.get("option1", "")).strip(),
                    str(question_data.get("option2", "")).strip(),
                    str(question_data.get("option3", "")).strip(),
                    str(question_data.get("option4", "")).strip()
                ]
                correctAnswer = str(question_data.get("correctAnswer", "")).strip()
                level = str(question_data.get("level", "")).strip().lower()
                tags = question_data.get("tags", [])

                # If level is missing or invalid, use 'general' as the default level
                if not level or level not in {"easy", "medium", "hard"}:
                    level = "general"

                # Skip rows with missing critical information
                if not all([question, options, correctAnswer]):
                    print(f"Skipping invalid question: {question_data}")
                    continue

                # Validate answer is one of the options
                if correctAnswer not in options:
                    print(f"Invalid answer for question: {question}")
                    continue

                # Prepare question data
                valid_question = {
                    "question_id": str(uuid.uuid4()),
                    "question": question,
                    "options": options,
                    "correctAnswer": correctAnswer,
                    "level": level,
                    "tags": tags
                }
                valid_questions.append(valid_question)

            # Check if the test document exists
            test_document = tests_collection.find_one({"test_id": test_id})
            if not test_document:
                print(f"Test document with test_id {test_id} not found.")
                return JsonResponse({"error": f"Test {test_id} not found."}, status=404)

            # Update the test document with the new questions
            result = tests_collection.update_one(
                {"test_id": test_id},
                {"$push": {"questions": {"$each": valid_questions}}}
            )

            # Debug: Check the result of insertion
            if result.modified_count > 0:
                print(f"Added {len(valid_questions)} questions to test {test_id}")
                return JsonResponse({
                    "message": f"Added {len(valid_questions)} questions to test {test_id} successfully!",
                    "inserted_count": len(valid_questions)
                }, status=200)
            else:
                print(f"No documents matched the query for test {test_id}")
                return JsonResponse({"error": f"Test {test_id} not found."}, status=404)

        except json.JSONDecodeError:
            print("Invalid JSON payload.")
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)
        except Exception as e:
            print(f"Unexpected error: {e}")
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request. Please send a JSON payload."}, status=400)


@csrf_exempt
def append_question_to_test(request):
    if request.method == "POST":
        try:
            # Parse the JSON payload
            data = json.loads(request.body)

            # Extract necessary information
            test_id = data.get("test_id")
            question = str(data.get("question", "")).strip()
            options = [
                str(data.get("option1", "")).strip(),
                str(data.get("option2", "")).strip(),
                str(data.get("option3", "")).strip(),
                str(data.get("option4", "")).strip()
            ]
            correctAnswer = str(data.get("correctAnswer", "")).strip()
            level = str(data.get("level", "")).strip().lower()
            tags = data.get("tags", [])

            # Validate input
            if not all([test_id, question, options, correctAnswer]):
                return JsonResponse({"error": "Missing required fields."}, status=400)

            # If level is missing or invalid, use 'general' as the default level
            if not level or level not in {"easy", "medium", "hard"}:
                level = "general"

            # Validate answer is one of the options
            if correctAnswer not in options:
                return JsonResponse({"error": "Invalid answer. The answer must be one of the provided options."}, status=400)

            # Prepare question data
            new_question = {
                "_id": {"$oid": str(ObjectId())},
                "question_id": str(uuid.uuid4()),
                "question": question,
                "options": options,
                "correctAnswer": correctAnswer,
                "level": level,
                "tags": tags,
                "answer": correctAnswer  # Include the answer field
            }

            # Update the test document to append the new question
            result = tests_collection.update_one(
                {"test_id": test_id},
                {"$push": {"questions": new_question}}
            )

            # Check update status
            if result.modified_count == 0:
                return JsonResponse({"error": "Test not found or question not added."}, status=404)

            return JsonResponse({"message": "Question appended to the test successfully"}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Only POST requests are allowed."}, status=405)


@csrf_exempt
def edit_question_in_test(request, test_id, question_id):
    if request.method == "PUT":
        try:
            # Parse JSON payload
            data = json.loads(request.body)

            # Extract and clean fields
            question = data.get("question", "").strip()
            options = data.get("options", [])
            correctAnswer = data.get("correctAnswer", "").strip()
            level = data.get("level", "general").strip().lower()
            tags = data.get("tags", [])
            blooms = data.get("blooms", "").strip()  # Extract blooms field

            # Input validation
            errors = []
            if not question:
                errors.append("Question text cannot be empty.")
            if len(options) < 2 or len(options) > 4:
                errors.append("Number of options must be between 2 and 4.")
            if len(set(options)) != len(options):
                errors.append("Options must be unique.")
            if not correctAnswer:
                errors.append("Answer cannot be empty.")
            if correctAnswer not in options:
                errors.append("Answer must be one of the provided options.")
            if errors:
                return JsonResponse({"error": errors}, status=400)

            # Build the update payload
            update_data = {
                "question": question,
                "options": options,
                "correctAnswer": correctAnswer,
                "level": level,
                "tags": tags,
                "blooms": blooms,  # Include blooms in the payload
            }

            # Execute the update query using question_id
            result = tests_collection.update_one(
                {"test_id": test_id, "questions.question_id": question_id},
                {"$set": {
                    "questions.$.question": question,
                    "questions.$.options": options,
                    "questions.$.correctAnswer": correctAnswer,
                    "questions.$.level": level,
                    "questions.$.tags": tags,
                    "questions.$.blooms": blooms  # Add blooms to the update
                }}
            )

            # Check update status
            if result.matched_count == 0:
                return JsonResponse({"error": "Question not found in the test"}, status=404)

            return JsonResponse({"message": "Question updated successfully"}, status=200)

        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Only PUT requests are allowed"}, status=405)