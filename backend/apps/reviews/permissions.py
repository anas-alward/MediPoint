from rest_framework.permissions import BasePermission



class IsReviewOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):

        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True 
        
        return request.user.is_patient and obj.patient == request.user.patient

class IsCommentOwner(BasePermission):

    
    
    def has_object_permission(self, request, view, obj):

        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True 
        
        return obj.user == request.user