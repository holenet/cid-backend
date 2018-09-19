from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from chatbot import views


urlpatterns = [
    path('hotels/', views.HotelList.as_view()),
    path('hotels/<int:pk>/', views.HotelDetail.as_view())
]

urlpatterns += format_suffix_patterns(urlpatterns)