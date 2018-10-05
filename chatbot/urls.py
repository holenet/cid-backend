from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from chatbot import views


urlpatterns = [
    path('artists/', views.ArtistList.as_view()),
    path('artists/<int:pk>/', views.ArtistDetail.as_view()),
    path('solo-artists/', views.SoloArtistList.as_view()),
    path('solo-artists/<int:pk>/', views.SoloArtistDetail.as_view()),
    path('group-artists/', views.GroupArtistList.as_view()),
    path('group-artists/<int:pk>/', views.GroupArtistDetail.as_view()),
]

urlpatterns += format_suffix_patterns(urlpatterns)