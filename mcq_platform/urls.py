"""mcq_platform URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from .views import *
from .mcqlibrary import save_selected_questions


urlpatterns = [
    path("save-data/", save_data,name = "saveData"),
    path("save-section-data/", save_section_data,name = "savesectionData"),
    path("start-contest/", start_contest, name="start_contest"),
    path("questions/", get_questions, name="get_questions"),
    path("questions/<str:question_id>/", update_mcqquestion, name="update_mcqquestion"), #manual update
    path("save-questions/", save_question, name="save_question"),
    path("api/assessment/questions/update", update_question, name="update_question"),
    path("finish-contest/", finish_contest,name="finish_contest"),
    path("bulk-upload/",bulk_upload_questions,name="bulkUpload"),
    path("publish/",publish_mcq,name="publish"),
    path("submit_assessment/",submit_mcq_assessment,name="submit_mcq_assessment"),
    path("get_mcqquestions/<str:contestId>/",get_mcqquestions,name="get_mcqquestions"),
    path("bulk-upload/",bulk_upload_questions,name="bulkUpload"),
    path("api/save-selected-questions/", save_selected_questions, name="save_selected_question"),
    path("student-report/<str:contestId>/<str:regno>/", get_student_report, name="student_report"),
    path("get-score/<str:contestId>/<str:regno>/", get_correct_answer, name="get_score"),
    path("publish-result/<str:contestId>/", publish_result, name="publish_result"),
    path("publish_mcq/", publish_mcq,name = "publish_mcq"),
    path('api/generate-questions/', generate_questions, name='generate_questions'),
    path("save-assessment-questions/", save_assessment_questions, name='save_assessment_questions'),
    path('delete-contest/<str:contest_id>/', delete_contest_by_id, name='delete-contest'),
    path('close-session/<str:contest_id>/', close_session, name='close_session'),
    path("delete-question/<str:question_id>/", delete_question, name="delete_question"),
    path('sections/<str:contest_id>/', get_section_questions_for_contest, name='get_section_questions_for_contest'),
    path('store-certificate/', store_certificate, name='store_certificate'),
    path("update-assessment/<str:contest_id>/", update_assessment, name="update_assessment"),
    path("reassign/<str:contest_id>/<str:student_id>/", reassign, name="reassign"),
    path('verify-certificate/<str:unique_id>/', verify_certificate, name='verify_certificate'),
    path('get_cert_date/', get_test_date, name='get_date'),

]
