from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from chatbot import views


urlpatterns = [
    path('auth/signup/', views.signup),
    path('auth/signin/', views.signin),
    path('auth/signout/', views.signout),
    path('auth/withdraw/', views.withdraw),
    path('my-info/', views.MuserDetail.as_view()),
    path('chat/', views.Chat.as_view()),
    path('chat/<int:pk>/', views.ChatDetail.as_view()),
    path('album-image/<int:album_id>/', views.album_image)
]

urlpatterns += format_suffix_patterns(urlpatterns)
