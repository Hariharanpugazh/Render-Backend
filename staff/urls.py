from django.urls import path
from .views import *
from .assessment import *
from . import assessment  # Import views from the current app
from . import studentsprofile
from staff.studentstats import studentstats
from .report import download_contest_data
from .studentstats import studentstats, mcq_student_results
from .assessment import create_assessment
from .Mcq_question import (
    bulk_upload, upload_single_question, fetch_all_questions,
    update_question, delete_question, create_test, update_test,
    delete_test, fetch_all_tests, bulk_upload_test, delete_question_from_test, fetch_questions_for_test, bulk_upload_questions_to_test,
    append_question_to_test,edit_question_in_test, 
)
from .views import *

urlpatterns = [
    # Authentication
    path("login/", staff_login, name="staff_login"),
    path("staff_logout/",staff_logout,name='staff_logout'),
    path("signup/", staff_signup, name="staff_signup"),
    path("forgot-password/", forgot_password, name="forgot_password"),
    path("reset-password/", reset_password, name="reset_password"),
    path("verify-token/", verify_token, name='verify_token'),
    path('api/create-assessment/', assessment.create_assessment, name='create_assessment'),
    path('studentprofile/', studentsprofile.student_profile, name='student_profile'),
    path('studentstats/<str:regno>/', studentstats, name='studentstats'),
    # path('api/assessment/<str:assessment_id>/', views.get_assessment, name='get_assessment'),
    path("profile/", get_staff_profile, name="get_staff_profile"),

    # path("get_students/", get_students, name="get_students"),

    # Dashboard
    path('contests/', fetch_contests, name='fetch_contests'),
    path('mcq/', fetch_mcq_assessments, name='fetch_mcq'),
    path('draft/', mcq_draft_data, name='draft_data'),
    path('delete-drafts/',delete_drafts, name='delete-draft'),
    # Assessment API
    path('api/create-assessment/', create_assessment, name='create_assessment'),

    # MCQ
    path("api/mcq-bulk-upload/", bulk_upload, name="mcq_bulk_upload"),
    path("api/upload-single-question/", upload_single_question, name="upload_single_question"),
    path("api/fetch-all-questions/", fetch_all_questions, name="fetch_all_questions"),
    path("api/update_question/<str:question_id>/", update_question, name="update_question"),
    path("api/delete_question/<str:question_id>/", delete_question, name="delete_question"),
    path('mcq_stats/<str:regno>/', mcq_student_results, name='mcq_student_results'),
    # path('api/update-assessment/<str:contest_id>/', assessment.update_assessment, name='update_assessment'),
    # ViewTest on admin
    path('students/stats', fetch_student_stats, name='student_stats'),
    path('api/contests/<str:contestId>/', view_test_details, name='view_test_details'),

    # Test Management
    path("api/create-test/", create_test, name="create_test"),
    path("api/update-test/<str:test_id>/", update_test, name="update_test"),
    path("api/delete-test/<str:test_id>/", delete_test, name="delete_test"),
    path("api/fetch-all-tests/", fetch_all_tests, name="fetch_all_tests"),
    path("api/fetch_questions_for_test/", fetch_questions_for_test, name="fetch_questions_for_test"),
    path("api/bulk-upload-to-test/", bulk_upload_test, name="bulk_upload_test"),
    path("api/delete-question-from-test/<str:test_id>/<str:question_id>/", delete_question_from_test, name="delete_question_from_test"),
    path('api/bulk-upload-questions-to-test/', bulk_upload_questions_to_test, name='bulk_upload_questions_to_test'),
    path('api/append-question-to-test/', append_question_to_test, name='append_question_to_test'),
    path('api/edit_question_in_test/<str:test_id>/<str:question_id>/', edit_question_in_test, name='edit_question_in_test'),


    # Report
    path('download-contest-data/<str:contest_id>/', download_contest_data, name='download_contest_data'),
    path('api/remove_student/<str:contestId>/<str:regno>/', remove_student_visibility, name='remove_student_visibility'),
]
