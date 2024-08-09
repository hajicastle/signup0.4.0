from rest_framework import generics, permissions, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import CustomUser, Profile, Project, InvitationLink, Friend
from .serializers import (
    CustomUserSerializer,
    ProfileCreateSerializer,
    ProfileUpdateSerializer,
    ProjectSerializer,
    InvitationLinkSerializer,
    FriendCreateSerializer,
    FriendUpdateSerializer,
    SearchSerializer,
)
import json
from django.core.mail import send_mail
from django.http import JsonResponse
from django.views import View
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from uuid import uuid4
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .HelperFuntions import get_user_distance
from django.db.models import Q
import logging
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model


class CreateUserView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        code = self.request.data.get("code")

        # code를 통해 db에서 해당 invite link 찾기
        if code:
            invitation = InvitationLink.objects.filter(link__contains=code).first()
            if not invitation:
                raise ValidationError("Invalid invitation code.")
            inviter_id = invitation.inviter_id
        else:
            inviter_id = None

        user = serializer.save()

        # 회원가입에 성공한 경우 Friend 추가
        if inviter_id:
            from_user = CustomUser.objects.get(id=inviter_id)
            to_user = user
            Friend.objects.create(
                from_user=from_user, to_user=to_user, status="accepted"
            )

        # 회원가입에 성공한 경우 초대 링크 상태를 accepted로 변경
        if invitation:
            invitation.status = "accepted"
            invitation.save()


class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


User = get_user_model()


class ChangePasswordView(generics.UpdateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        new_password = request.data.get("new_password")
        if not new_password:
            return Response(
                {"detail": "New password is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instance.set_password(new_password)
        instance.save()
        return Response(
            {"detail": "Password changed successfully."}, status=status.HTTP_200_OK
        )


class DeleteUserView(generics.DestroyAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        user.delete()
        return Response(
            {"detail": "User deleted successfully."}, status=status.HTTP_204_NO_CONTENT
        )


class CurrentProfileView(generics.RetrieveAPIView):
    serializer_class = ProfileCreateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return Profile.objects.get(user=self.request.user)


class ProfileUpdateView(generics.UpdateAPIView):
    queryset = Profile.objects.all()
    serializer_class = ProfileUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return Profile.objects.get(user=self.request.user)


class ProjectListCreate(generics.ListCreateAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]
    queryset = Project.objects.all()

    def perform_create(self, serializer):
        if serializer.is_valid():
            serializer.save(
                user=self.request.user
            )  # serializers.py에서 user가 read_only라서 여기서 해줘야함
        else:
            print(serializer.errors)


class ProjectDelete(generics.DestroyAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Project.objects.filter(user=user)  # user가 user인 project만 필터


@method_decorator(csrf_exempt, name="dispatch")
class SendCodeView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            email = data.get("email")
            code = data.get("code")
        except (json.JSONDecodeError, KeyError):
            return JsonResponse({"error": "Invalid JSON data"}, status=400)

        if not email or not code:
            return JsonResponse({"error": "Email and code are required"}, status=400)

        send_mail(
            "Your verification code",
            f"Your verification code is {code}",
            "from@example.com",
            [email],
            fail_silently=False,
        )

        return JsonResponse({"message": "Verification code sent"}, status=200)


class InvitationLinkList(generics.ListAPIView):
    serializer_class = InvitationLinkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return InvitationLink.objects.filter(inviter=user)


class CreateInvitationLinkView(generics.CreateAPIView):
    serializer_class = InvitationLinkSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request):
        unique_code = str(uuid4())
        name = request.data.get("name", "")

        invitation_link = InvitationLink.objects.create(
            inviter=request.user,
            invitee_name=name,
            link=f"http://localhost:5173/welcome?code={unique_code}",
        )

        return Response(
            {"link": invitation_link.link, "id": invitation_link.id}, status=201
        )


class WelcomeView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        code = request.query_params.get("code", None)
        if code:
            # code로 InvitationLink 객체를 찾기
            invite_link = get_object_or_404(InvitationLink, link__endswith=code)
            inviter_name = invite_link.inviter.profile.user_name
            invitee_name = invite_link.invitee_name

            # Calculate the expiration date (7 days after creation)
            expired_date = invite_link.created_at + timezone.timedelta(days=7)
            current_date = timezone.now()

            # Check if the invitation link is expired
            if current_date > expired_date:
                invite_link.status = "expired"
                invite_link.save()
                return Response({"message": "Invitation link is expired"}, status=400)

            # Check if the invitation link is expired
            if invite_link.status == "accepted":
                return Response({"message": "Invitation link already used"}, status=400)

            return Response(
                {
                    "inviter_name": inviter_name,
                    "invitee_name": invitee_name,
                }
            )
        return Response({"message": "Invalid invitation code."}, status=400)


class InvitationLinkDelete(generics.DestroyAPIView):
    serializer_class = InvitationLinkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return InvitationLink.objects.filter(inviter=user)


logger = logging.getLogger(__name__)


class ListCreateFriendView(generics.ListCreateAPIView):
    serializer_class = FriendCreateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Friend.objects.filter(from_user=user) | Friend.objects.filter(
            to_user=user
        )

    def perform_create(self, serializer):
        from_user = self.request.user
        to_user_id = serializer.validated_data.get("to_user").id
        try:
            to_user = CustomUser.objects.get(id=to_user_id)
            logger.info(
                f"Creating friendship: from_user={from_user.email}, to_user={to_user.email}"
            )
            serializer.save(from_user=from_user, to_user=to_user, status="accepted")
        except CustomUser.DoesNotExist:
            logger.error(f"User with id {to_user_id} does not exist")
            raise ValidationError("User with this ID does not exist.")


class FriendUpdateView(generics.UpdateAPIView):
    serializer_class = FriendUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Friend.objects.filter(Q(from_user=user) | Q(to_user=user))

    def perform_update(self, serializer):
        print(
            f"Performing update with data: {serializer.validated_data}"
        )  # Debugging line
        super().perform_update(serializer)


class FriendDeleteView(generics.DestroyAPIView):
    serializer_class = FriendCreateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Friend.objects.filter(
            Q(from_user=user) | Q(to_user=user)
        )  # user가 포함된 친구 필터


class GetUserDistanceAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        user = request.user
        target_user_id = kwargs.get("pk")
        try:
            target_user = CustomUser.objects.get(id=target_user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "Target user not found."}, status=status.HTTP_404_NOT_FOUND
            )

        distance = get_user_distance(user, target_user)
        return Response({"distance": distance}, status=status.HTTP_200_OK)


class SearchUsersAPIView(generics.ListAPIView):
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]

    # 변수를 쿼리가 아닌 JSON 형식으로 전달받기 위해 POST 요청으로 변경
    # GET 요청 시 쿼리를 포함한 url이 너무 길어져서 반려.
    def post(self, request, *args, **kwargs):
        serializer = SearchSerializer(data=request.data)
        if serializer.is_valid():
            query = serializer.validated_data.get("q", "")
            degrees = serializer.validated_data.get("degree", [])
            majors = serializer.validated_data.get("major", [])

            print("Received Degrees:", degrees)

            # 전체 프로필을 가져옵니다.
            filtered_profiles = Profile.objects.all()

            # 1. 검색 쿼리로 필터링
            if query != "":
                filtered_profiles = filtered_profiles.filter(
                    keywords__keyword__icontains=query
                )

            # 2. 전공 필터링
            if majors:
                filtered_profiles = filtered_profiles.filter(major__in=majors)

            # 3. 촌수 필터링 (비어있는 경우 1, 2, 3촌 다 포함)
            if not degrees:
                degrees = [1, 2, 3]
            degrees = list(map(int, degrees))
            user = self.request.user
            degree_filtered_profiles = []
            print("Filtered Degrees:", degrees)

            for profile in filtered_profiles:
                target_user = profile.user
                distance = get_user_distance(user, target_user)
                if distance is not None and distance in degrees:
                    degree_filtered_profiles.append(profile)

            filtered_profiles = degree_filtered_profiles
            print("Filtered Profiles:", filtered_profiles)

            custom_users = CustomUser.objects.filter(profile__in=filtered_profiles)

            serializer = self.get_serializer(custom_users, many=True)
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
