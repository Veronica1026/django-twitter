from friendships.api.paginations import FriendshipPagination
from friendships.api.serializers import (
    FollowingSerializer,
    FollowerSerializer,
    FriendshipSerializerForCreate,
)
from django.contrib.auth.models import User
from friendships.models import Friendship
from friendships.services import FriendshipService
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response


class FriendshipViewSet(viewsets.GenericViewSet):
    # POST /api/friendships/1/follow means for current logged in user to follow the user with id=1
    # so for queryset here we need User.objects.all()
    # if we use Friendship.object.all, there will be "404 not found"
    # because detail=True means the action will by default go and use get_object()
    # which is queryset.filter(pk=1) to query if the object exists
    queryset = User.objects.all()
    serializer_class = FriendshipSerializerForCreate

    # generally, different views needs different pagination rules, so we need to define our own pagination rules
    pagination_class = FriendshipPagination

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    def followers(self, request, pk):
        friendships = Friendship.objects.filter(to_user_id=pk).order_by('-created_at')
        page = self.paginate_queryset(friendships)
        serializer = FollowerSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data);

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    def followings(self, request, pk):
        friendships = Friendship.objects.filter(from_user_id=pk).order_by('-created_at')
        page = self.paginate_queryset(friendships)
        serializer = FollowingSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    def follow(self, request, pk):
        # egde case check: duplicate follow action (e.g. multiple clicks from frontend)
        # silent processing. No need to report error.
        # because this kind of duplicated operation are mostly because of internet delay,
        if Friendship.objects.filter(from_user=request.user, to_user=pk).exists():
            return Response({
                'success': True,
                'duplicate': True,
            }, status=status.HTTP_201_CREATED)
        serializer = FriendshipSerializerForCreate(data={
            'from_user_id': request.user.id,
            'to_user_id': pk,
        })
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
        instance = serializer.save()
        FriendshipService.invalidate_following_cache(request.user.id)
        return Response(
            FollowingSerializer(instance, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    def unfollow(self, request, pk):
        # raise 404 if no user with id=pk
        unfollow_user = self.get_object()

        # the type of pk is str, so we need to convert it to int
        if request.user.id == int(pk):
            return Response({
                'success': False,
                'message': 'You cannot unfollow yourself',
            }, status=status.HTTP_400_BAD_REQUEST)

        """
        the delete operation of a Queryset returns two values:
        one is how many data is deleted, the other is how many is deleted for each type
        why can deletions on multiple types happen? This happens if there are cascade deletion on foreign keys
        e.g. if an attribute of model A is modelB, and we set on_delete=models.CASCADE, 
        when some data from model B is deleted, the relevant records in A will also get deleted
        therefore CASCADE is a dangerous operation, don't use it unless you are 100% sure
        recommended alternative: on_delete=models.SET_NULL, which saves us from the domino effect of accidental deletion
        
        """
        deleted, _ = Friendship.objects.filter(
            from_user=request.user,
            to_user=unfollow_user,
        ).delete()
        FriendshipService.invalidate_following_cache(request.user.id)
        return Response({
            'success': True,
            'deleted': deleted
        })

    def list(self, request):
        return Response({'message': 'this is friendships home page'})
