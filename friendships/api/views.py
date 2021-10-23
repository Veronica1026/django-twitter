from friendships.api.serializers import (
    FollowingSerializer,
    FollowerSerializer,
    FriendshipSerializerForCreate,
)
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from friendships.models import HBaseFollowing, HBaseFollower, Friendship
from friendships.services import FriendshipService
from gatekeeper.models import GateKeeper
from ratelimit.decorators import ratelimit
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from utils.paginations import EndlessPagination


class FriendshipViewSet(viewsets.GenericViewSet):
    # POST /api/friendships/1/follow means for current logged in user to follow the user with id=1
    # so for queryset here we need User.objects.all()
    # if we use Friendship.object.all, there will be "404 not found"
    # because detail=True means the action will by default go and use get_object()
    # which is queryset.filter(pk=1) to query if the object exists
    queryset = User.objects.all()
    serializer_class = FriendshipSerializerForCreate

    # generally, different views needs different pagination rules, so we need to define our own pagination rules
    pagination_class = EndlessPagination

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    @method_decorator(ratelimit(key='user_or_ip', rate='3/s', method='GET', block=True))
    def followers(self, request, pk):
        if GateKeeper.is_switched_on('switch_friendship_to_hbase'):
            page = self.paginator.paginate_hbase(HBaseFollower, (pk,), request)
        else:
            friendships = Friendship.objects.filter(to_user_id=pk).order_by('-created_at')
            page = self.paginate_queryset(friendships)
        serializer = FollowerSerializer(page, many=True, context={'request': request})
        return self.paginator.get_paginated_response(serializer.data);

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    @method_decorator(ratelimit(key='user_or_ip', rate='3/s', method='GET', block=True))
    def followings(self, request, pk):
        if GateKeeper.is_switched_on('switch_friendship_to_hbase'):
            page = self.paginator.paginate_hbase(HBaseFollowing, (pk,), request)
        else:
            friendships = Friendship.objects.filter(from_user_id=pk).order_by('-created_at')
            page = self.paginate_queryset(friendships)
        serializer = FollowingSerializer(page, many=True, context={'request': request})
        return self.paginator.get_paginated_response(serializer.data)

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    @method_decorator(ratelimit(key='user', rate='10/s', method='POST', block=True))
    def follow(self, request, pk):
        # egde case check: duplicate follow action (e.g. multiple clicks from frontend)
        # silent processing. No need to report error.
        # because this kind of duplicated operation are mostly because of internet delay,
        if FriendshipService.has_followed(request.user.id, int(pk)):
            return Response({
                'success': True,
                'duplicate': True,
                'error': [{'pk': f'you have followed the user with id={pk}'}],
            }, status=status.HTTP_400_BAD_REQUEST)
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
        return Response(
            FollowingSerializer(instance, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    @method_decorator(ratelimit(key='user', rate='10/s', method='POST', block=True))
    def unfollow(self, request, pk):
        # raise 404 if no user with id=pk
        unfollow_user = self.get_object()

        # the type of pk is str, so we need to convert it to int
        if request.user.id == int(pk):
            return Response({
                'success': False,
                'message': 'You cannot unfollow yourself',
            }, status=status.HTTP_400_BAD_REQUEST)

        deleted = FriendshipService.unfollow(request.user.id, int(pk))
        return Response({
            'success': True,
            'deleted': deleted
        })

    def list(self, request):
        return Response({'message': 'this is friendships home page'})
