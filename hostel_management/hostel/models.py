from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q

# Create your models here.

class StudentProfile(models.Model):
  user=models.OneToOneField(
                            User,
                            on_delete=models.CASCADE,
                            related_name='student_profile'
                            )
  phone=models.CharField(max_length=15)
  department=models.CharField(max_length=50)
  academic_year=models.CharField(max_length=20)
  address=models.TextField()

  def __str__(self):
    return self.user.username

class Room(models.Model):

  ROOM_TYPES=[
    ('dormitory','Dormitory'),
    ('twin','Twin Bed'),
  ]

  room_number=models.CharField(max_length=10,unique=True)
  room_type=models.CharField(max_length=20,choices=ROOM_TYPES)
  monthly_rate=models.DecimalField(max_digits=8,decimal_places=2)
  facilities=models.TextField(blank=True)
  is_active=models.BooleanField(default=True)
  created_at=models.DateTimeField(auto_now_add=True)

  @property
  def capacity(self):
    return {
      'dormitory':4,
      'twin':2
    }.get(self.room_type,0)

  def __str__(self):
    return f"{self.room_number} - {self.get_room_type_display()}"


class Booking(models.Model):

  STATUS_CHOICES=[
    ('pending','Pending'),
    ('approved','Approved'),
    ('rejected','Rejected'),
    ('completed','Completed')
  ]

  student=models.ForeignKey(
    StudentProfile,
    on_delete=models.PROTECT,
    related_name='bookings'
  )

  requested_room_type=models.CharField(max_length=20,choices=Room.ROOM_TYPES)

  room=models.ForeignKey(
    Room,
    on_delete=models.PROTECT,
    null=True,
    blank=True,
    related_name='bookings'
  ) 

  requested_date=models.DateTimeField(auto_now_add=True)

  status=models.CharField(max_length=20,choices=STATUS_CHOICES,default="pending")

  allocated_date=models.DateField(null=True,blank=True)
  vacated_date=models.DateField(null=True,blank=True)
  monthly_rate_at_allocation=models.DecimalField(max_digits=8,decimal_places=2,null=True,blank=True)

  class Meta:
    constraints=[
      models.UniqueConstraint(
        fields=['student'],
        condition=Q(status__in=['pending','approved']),
        name="one_active_booking_per_student"
      )
    ]

  def __str__(self):
    return f"{self.student.user.username} - {self.status}"