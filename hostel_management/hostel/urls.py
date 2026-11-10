from django.urls import path
from . import views

urlpatterns=[
  path('',views.home,name='home'),
  path('register/',views.register,name='register'),
  path('login/',views.login_view,name='login'),
  path('logout/',views.logout_view,name='logout'),
  path('admin-dashboard/',views.admin_dashboard,name='admin_dashboard'),
  path('student-dashboard/',views.student_dashboard,name='student_dashboard'),
  path('rooms/', views.rooms, name='rooms'),
  path('my-bookings/', views.my_bookings, name='my_bookings'),
  path('my-profile/', views.my_profile, name='my_profile'),
  path('edit-profile/', views.edit_profile, name='edit_profile'),
  path('admin_rooms/',views.admin_rooms,name="admin_rooms"),
  path('admin_rooms/<int:room_id>/',views.admin_room_details,name="admin_room_details"),
  path('admin-students/', views.admin_students, name='admin_students'),
  path('admin-students/<int:student_id>/', views.admin_student_details, name='admin_student_details'),
  path('admin-bookings/', views.admin_bookings, name='admin_bookings'),
  path('admin-bookings/<int:booking_id>/approve/',views.approve_booking,name='approve_booking'),
  path('admin-bookings/<int:booking_id>/reject/',views.reject_booking,name='reject_booking'),
  path('admin-bookings/<int:booking_id>/allocate/', views.allocate_room,name='allocate_room'),
  path('admin-bookings/<int:booking_id>/complete/',views.complete_booking,name='complete_booking'),
]