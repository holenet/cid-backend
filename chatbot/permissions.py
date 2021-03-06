from rest_framework import permissions


class IsExactMuser(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.username == obj.username
