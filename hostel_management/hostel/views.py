from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth import login as auth_login
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import logout
from . forms import StudentRegistrationForm, UserEmailForm, StudentProfileForm
from django.contrib.auth.decorators import login_required,user_passes_test
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from .models import Booking,Room
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.db import transaction
from django.utils.dateparse import parse_date  


# Create your views here.

def home(request):
  return render(request,'home.html')

def register(request):

  if request.method=="POST":

    form=StudentRegistrationForm(request.POST)
    if form.is_valid():
      form.save()
      return redirect('login')

  else:
    form=StudentRegistrationForm()

  return render(request,'register.html',{'form':form})

def login_view(request):

  if request.method=="POST":

    form=AuthenticationForm(request,data=request.POST)

    if form.is_valid():
      user=form.get_user()
      auth_login(request,user)

      if user.is_staff:
        return redirect('admin_dashboard')
      else:
        return redirect('student_dashboard')
      
  else:
    form=AuthenticationForm()

  return render(request,'login.html',{'form':form})


@require_POST
def logout_view(request):
  logout(request)
  return redirect('home')



from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.utils import timezone

from .models import Room, Booking, StudentProfile


@login_required
@user_passes_test(lambda user: user.is_staff, login_url='login')
def admin_dashboard(request):

    today = timezone.localdate()

    # Get all active rooms
    rooms = Room.objects.filter(is_active=True).order_by('id')

    # Find bookings of students currently staying in the hostel
    current_bookings = Booking.objects.filter(
        status='approved',
        room__is_active=True,
        allocated_date__lte=today
    ).filter(
        Q(vacated_date__isnull=True) |
        Q(vacated_date__gt=today)
    ).select_related('student__user', 'room')

    # Calculate total hostel statistics
    total_rooms = rooms.count()

    total_capacity = sum(room.capacity for room in rooms)

    current_students = current_bookings.values(
        'student'
    ).distinct().count()

    available_beds = total_capacity - current_students

    # Add occupancy details to each room
    occupied_rooms = 0
    dormitory_rooms = []
    twin_rooms = []

    for room in rooms:

        room_students = current_bookings.filter(room=room)

        occupied = room_students.count()
        available = room.capacity - occupied

        room.occupied = occupied
        room.available = available
        room.residents = room_students

        if occupied == 0:
            room.occupancy_status = 'Empty'
        elif available == 0:
            room.occupancy_status = 'Full'
        else:
            room.occupancy_status = 'Partially Occupied'

        if occupied > 0:
            occupied_rooms += 1

        if room.room_type == 'dormitory':
            dormitory_rooms.append(room)
        else:
            twin_rooms.append(room)

    # Count pending booking requests
    pending_bookings = Booking.objects.filter(
        status='pending'
    ).count()

    # Get the five most recent bookings
    recent_bookings = Booking.objects.select_related(
        'student__user',
        'room'
    ).order_by('-requested_date')[:5]

    # Get the five recently registered students
    recent_students = StudentProfile.objects.select_related(
        'user'
    ).order_by('-user__date_joined')[:5]

    context = {
        'total_rooms': total_rooms,
        'total_capacity': total_capacity,
        'current_students': current_students,
        'available_beds': available_beds,
        'occupied_rooms': occupied_rooms,
        'pending_bookings': pending_bookings,
        'dormitory_rooms': dormitory_rooms,
        'twin_rooms': twin_rooms,
        'recent_bookings': recent_bookings,
        'recent_students': recent_students,
    }

    return render(request, 'admin_dashboard.html', context)



@login_required
@user_passes_test(lambda user: not user.is_staff, login_url='login')
def student_dashboard(request):

    profile = request.user.student_profile
    today = timezone.localdate()

    # Get the latest booking
    latest_booking = profile.bookings.order_by(
        '-requested_date'
    ).first()

    # Find the current allocated booking
    current_booking = profile.bookings.filter(
        status='approved',
        room__isnull=False,
        allocated_date__lte=today
    ).filter(
        Q(vacated_date__isnull=True) |
        Q(vacated_date__gt=today)
    ).order_by('-allocated_date').first()

    # Find pending booking
    pending_booking = profile.bookings.filter(
        status='pending'
    ).order_by('-requested_date').first()

    # Determine room status
    if current_booking:
        room_status = "Staying"
        allocated_room = current_booking.room.room_number

    elif pending_booking:
        room_status = "Pending"
        allocated_room = "--"

    else:
        room_status = "Not Allocated"
        allocated_room = "--"

    # Determine booking status
    if latest_booking:
        booking_status = latest_booking.get_status_display()
    else:
        booking_status = "No Bookings"

    # Check profile completion
    if all([
        profile.phone,
        profile.department,
        profile.academic_year,
        profile.address
    ]):
        profile_status = "Complete"
    else:
        profile_status = "Incomplete"

    context = {
        'current_booking': current_booking,
        'latest_booking': latest_booking,
        'room_status': room_status,
        'booking_status': booking_status,
        'allocated_room': allocated_room,
        'profile_status': profile_status,
    }

    return render(request, 'student_dashboard.html', context)


def rooms(request):

    # Get one active room of each type for displaying its details
    dormitory_room = Room.objects.filter(
        room_type='dormitory',
        is_active=True
    ).first()

    twin_room = Room.objects.filter(
        room_type='twin',
        is_active=True
    ).first()

    if request.method == 'POST':

        # Only logged-in students can submit requests
        if not request.user.is_authenticated:
            return redirect('login')

        if request.user.is_staff:
            return redirect('admin_dashboard')

        requested_type = request.POST.get('requested_room_type')

        # Validate selected room type
        valid_types = dict(Room.ROOM_TYPES)

        if requested_type not in valid_types:
            messages.error(request, 'Please select a valid room type.')
            return redirect('rooms')

        # Check whether the selected room type has active rooms
        selected_room = Room.objects.filter(
            room_type=requested_type,
            is_active=True
        ).first()

        if not selected_room:
            messages.error(request, 'This room type is currently unavailable.')
            return redirect('rooms')

        profile = request.user.student_profile

        # Prevent multiple active booking requests
        existing_booking = profile.bookings.filter(
            status__in=['pending', 'approved']
        ).exists()

        if existing_booking:
            messages.error(
                request,
                'You already have an active booking request.'
            )
            return redirect('rooms')

        # Create booking request
        Booking.objects.create(
            student=profile,
            requested_room_type=requested_type
        )

        messages.success(
            request,
            'Your booking request has been submitted successfully.'
        )

        return redirect('rooms')

    context = {
        'dormitory_room': dormitory_room,
        'twin_room': twin_room,
    }

    return render(request, 'rooms.html', context)


@login_required
@user_passes_test(lambda user: not user.is_staff, login_url='login')
def my_bookings(request):

    profile = request.user.student_profile

    # Current pending or approved booking
    current_booking = profile.bookings.filter(
        status__in=['pending', 'approved']
    ).order_by('-requested_date').first()

    # Previous rejected or completed bookings
    booking_history = profile.bookings.filter(
        status__in=['rejected', 'completed']
    ).order_by('-requested_date')

    context = {
        'current_booking': current_booking,
        'booking_history': booking_history,
    }

    return render(request, 'my_bookings.html', context)

@login_required
@user_passes_test(lambda user: not user.is_staff, login_url='login')
def my_profile(request):

    profile = request.user.student_profile

    context = {
        'profile': profile,
    }

    return render(request, 'my_profile.html', context)

@login_required
@user_passes_test(lambda user: not user.is_staff, login_url='login')
def edit_profile(request):

    profile = request.user.student_profile

    if request.method == 'POST':

        user_form = UserEmailForm(
            request.POST,
            instance=request.user
        )

        profile_form = StudentProfileForm(
            request.POST,
            instance=profile
        )

        if user_form.is_valid() and profile_form.is_valid():

            user_form.save()
            profile_form.save()

            messages.success(
                request,
                'Your profile has been updated successfully.'
            )

            return redirect('my_profile')

    else:

        user_form = UserEmailForm(instance=request.user)
        profile_form = StudentProfileForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }

    return render(request, 'edit_profile.html', context)



@login_required
@user_passes_test(lambda user: user.is_staff, login_url='login')
def admin_rooms(request):

    today = timezone.localdate()

    # Get all rooms
    rooms = Room.objects.all().order_by('id')

    # Search by room number
    search_query = request.GET.get('search', '').strip()

    if search_query:
        rooms = rooms.filter(room_number__icontains=search_query)

    # Filter by room type
    selected_type = request.GET.get('room_type', '')

    if selected_type in dict(Room.ROOM_TYPES):
        rooms = rooms.filter(room_type=selected_type)

    # Get current residents
    current_bookings = Booking.objects.filter(
        status='approved',
        room__isnull=False,
        allocated_date__lte=today
    ).filter(
        Q(vacated_date__isnull=True) |
        Q(vacated_date__gt=today)
    ).select_related('student__user', 'room')

    # Calculate occupancy for each room
    total_rooms = Room.objects.count()
    total_capacity = sum(room.capacity for room in Room.objects.all())

    occupied_beds = 0
    occupied_rooms = 0

    for room in rooms:
        residents = current_bookings.filter(room=room)

        room.occupied = residents.count()
        room.available = room.capacity - room.occupied
        room.residents = residents

        if room.occupied == 0:
            room.occupancy_status = 'Empty'
        elif room.available == 0:
            room.occupancy_status = 'Full'
        else:
            room.occupancy_status = 'Partially Occupied'

        occupied_beds += room.occupied

        if room.occupied > 0:
            occupied_rooms += 1

    # Overall statistics (not affected by filters)
    all_current_bookings = current_bookings

    total_occupied_beds = all_current_bookings.count()

    context = {
        'rooms': rooms,
        'total_rooms': total_rooms,
        'total_capacity': total_capacity,
        'occupied_beds': total_occupied_beds,
        'available_beds': total_capacity - total_occupied_beds,
        'occupied_rooms': occupied_rooms,
        'search_query': search_query,
        'selected_type': selected_type,
    }

    return render(request, 'admin_rooms.html', context)


@login_required
@user_passes_test(lambda user: user.is_staff, login_url='login')
def admin_room_details(request, room_id):

    today = timezone.localdate()

    room = get_object_or_404(Room, id=room_id)

    # Get students currently staying in this room
    current_residents = Booking.objects.filter(
        room=room,
        status='approved',
        allocated_date__lte=today
    ).filter(
        Q(vacated_date__isnull=True) |
        Q(vacated_date__gt=today)
    ).select_related('student__user').order_by('allocated_date')

    occupied = current_residents.count()
    available = room.capacity - occupied

    if occupied == 0:
        occupancy_status = 'Empty'
    elif available == 0:
        occupancy_status = 'Full'
    else:
        occupancy_status = 'Partially Occupied'

    context = {
        'room': room,
        'current_residents': current_residents,
        'occupied': occupied,
        'available': available,
        'occupancy_status': occupancy_status,
    }

    return render(request, 'admin_room_details.html', context)




@login_required
@user_passes_test(lambda user: user.is_staff, login_url='login')
def admin_students(request):

    today = timezone.localdate()

    # Fetch students along with their booking records
    all_students = list(
        StudentProfile.objects.select_related('user')
        .prefetch_related('bookings__room')
        .order_by('-user__date_joined')
    )

    total_students = len(all_students)
    currently_staying = 0
    pending_student_count = 0
    not_allocated = 0
    completed_students = 0

    # Determine each student's accommodation status
    for student in all_students:

        bookings = list(student.bookings.all())

        current_bookings = [
            booking for booking in bookings
            if booking.status == 'approved'
            and booking.room is not None
            and booking.allocated_date is not None
            and booking.allocated_date <= today
            and (
                booking.vacated_date is None
                or booking.vacated_date > today
            )
        ]

        pending_bookings = [
            booking for booking in bookings
            if booking.status == 'pending'
        ]

        future_bookings = [
            booking for booking in bookings
            if booking.status == 'approved'
            and booking.room is not None
            and booking.allocated_date is not None
            and booking.allocated_date > today
        ]

        completed_bookings = [
            booking for booking in bookings
            if booking.status == 'completed'
        ]

        if current_bookings:
            student.accommodation_status = 'Staying'
            student.current_booking = current_bookings[-1]
            currently_staying += 1

        elif pending_bookings:
            student.accommodation_status = 'Pending'
            student.current_booking = pending_bookings[-1]
            pending_student_count += 1

        elif future_bookings:
            student.accommodation_status = 'Allocated'
            student.current_booking = future_bookings[-1]

        elif completed_bookings:
            student.accommodation_status = 'Completed'
            student.current_booking = completed_bookings[-1]
            completed_students += 1

        else:
            student.accommodation_status = 'Not Allocated'
            student.current_booking = None
            not_allocated += 1

    # Search filter
    students = all_students
    search_query = request.GET.get('search', '').strip().lower()

    if search_query:
        students = [
            student for student in students
            if search_query in student.user.username.lower()
            or search_query in student.user.first_name.lower()
            or search_query in student.user.last_name.lower()
            or search_query in student.user.email.lower()
            or search_query in student.department.lower()
        ]

    # Department filter
    selected_department = request.GET.get('department', '')

    if selected_department:
        students = [
            student for student in students
            if student.department == selected_department
        ]

    # Accommodation status filter
    selected_status = request.GET.get('status', '')

    if selected_status:
        students = [
            student for student in students
            if student.accommodation_status == selected_status
        ]

    context = {
        'students': students,
        'total_students': total_students,
        'currently_staying': currently_staying,
        'pending_requests': Booking.objects.filter(
            status='pending'
        ).count(),
        'not_allocated': not_allocated,
        'completed_students': completed_students,
        'search_query': search_query,
        'selected_department': selected_department,
        'selected_status': selected_status,
        'departments': StudentProfile.objects.values_list(
            'department', flat=True
        ).distinct().order_by('department'),
    }

    return render(request, 'admin_students.html', context)


@login_required
@user_passes_test(lambda user: user.is_staff, login_url='login')
def admin_student_details(request, student_id):

    today = timezone.localdate()

    # Get the selected student
    student = get_object_or_404(
        StudentProfile.objects.select_related('user'),
        id=student_id
    )

    # Get all bookings belonging to this student
    bookings = student.bookings.select_related(
        'room'
    ).order_by('-requested_date')

    # Find the current accommodation
    current_booking = bookings.filter(
        status='approved',
        room__isnull=False,
        allocated_date__lte=today
    ).filter(
        Q(vacated_date__isnull=True) |
        Q(vacated_date__gt=today)
    ).first()

    # Find the latest pending request
    pending_booking = bookings.filter(
        status='pending'
    ).first()

    # Determine accommodation status
    if current_booking:
        accommodation_status = 'Staying'

    elif pending_booking:
        accommodation_status = 'Pending'

    else:
        future_booking = bookings.filter(
            status='approved',
            room__isnull=False,
            allocated_date__gt=today
        ).first()

        if future_booking:
            accommodation_status = 'Allocated'

        elif bookings.filter(status='completed').exists():
            accommodation_status = 'Completed'

        else:
            accommodation_status = 'Not Allocated'

    context = {
        'student': student,
        'bookings': bookings,
        'current_booking': current_booking,
        'pending_booking': pending_booking,
        'accommodation_status': accommodation_status,
    }

    return render(
        request,
        'admin_student_details.html',
        context
    )


@login_required
@user_passes_test(lambda user: user.is_staff, login_url='login')
def admin_bookings(request):

    # Get all booking records
    all_bookings = Booking.objects.select_related(
        'student__user',
        'room'
    ).order_by('-requested_date')

    # Calculate statistics
    total_bookings = all_bookings.count()
    pending_bookings = all_bookings.filter(status='pending').count()
    approved_bookings = all_bookings.filter(status='approved').count()
    rejected_bookings = all_bookings.filter(status='rejected').count()
    completed_bookings = all_bookings.filter(status='completed').count()

    # Search by student details
    search_query = request.GET.get('search', '').strip()

    bookings = all_bookings

    if search_query:
        bookings = bookings.filter(
            Q(student__user__username__icontains=search_query) |
            Q(student__user__first_name__icontains=search_query) |
            Q(student__user__last_name__icontains=search_query) |
            Q(student__user__email__icontains=search_query) |
            Q(room__room_number__icontains=search_query)
        )

    # Filter by booking status
    selected_status = request.GET.get('status', '')

    valid_statuses = dict(Booking.STATUS_CHOICES)

    if selected_status in valid_statuses:
        bookings = bookings.filter(status=selected_status)
    else:
        selected_status = ''

    # Filter by requested room type
    selected_room_type = request.GET.get('room_type', '')

    valid_room_types = dict(Room.ROOM_TYPES)

    if selected_room_type in valid_room_types:
        bookings = bookings.filter(
            requested_room_type=selected_room_type
        )
    else:
        selected_room_type = ''

    available_rooms = Room.objects.filter(
    is_active=True
     ).order_by('room_number')

    context = {
        'bookings': bookings,
        'total_bookings': total_bookings,
        'pending_bookings': pending_bookings,
        'approved_bookings': approved_bookings,
        'rejected_bookings': rejected_bookings,
        'completed_bookings': completed_bookings,
        'search_query': search_query,
        'selected_status': selected_status,
        'selected_room_type': selected_room_type,
        'status_choices': Booking.STATUS_CHOICES,
        'room_types': Room.ROOM_TYPES,
        'available_rooms': available_rooms,
    }

    return render(request, 'admin_bookings.html', context)


@login_required
@user_passes_test(lambda user: user.is_staff, login_url='login')
@require_POST
def allocate_room(request, booking_id):

    allocation_date = parse_date(
        request.POST.get('allocation_date', '')
    )

    room_id = request.POST.get('room_id')

    if not allocation_date:
        messages.error(request, 'Please select a valid allocation date.')
        return redirect('admin_bookings')

    if allocation_date < timezone.localdate():
        messages.error(request, 'Allocation date cannot be in the past.')
        return redirect('admin_bookings')

    with transaction.atomic():

        booking = get_object_or_404(
            Booking.objects.select_for_update(),
            id=booking_id
        )

        if booking.status != 'approved' or booking.room_id is not None:
            messages.error(
                request,
                'This booking is not eligible for room allocation.'
            )
            return redirect('admin_bookings')

        room = get_object_or_404(
            Room.objects.select_for_update(),
            id=room_id,
            is_active=True
        )

        if room.room_type != booking.requested_room_type:
            messages.error(
                request,
                'Please select a room matching the requested room type.'
            )
            return redirect('admin_bookings')

        # Find occupants on the selected allocation date
        occupied_beds = Booking.objects.filter(
            room=room,
            status='approved',
            allocated_date__lte=allocation_date
        ).filter(
            Q(vacated_date__isnull=True) |
            Q(vacated_date__gt=allocation_date)
        ).count()

        if occupied_beds >= room.capacity:
            messages.error(
                request,
                'This room has no available beds on the selected date.'
            )
            return redirect('admin_bookings')

        # Save allocation
        booking.room = room
        booking.allocated_date = allocation_date
        booking.monthly_rate_at_allocation = room.monthly_rate
        booking.save()

    messages.success(
        request,
        f'Room {room.room_number} allocated successfully.'
    )

    return redirect('admin_bookings')


@login_required
@user_passes_test(lambda user: user.is_staff, login_url='login')
@require_POST
def approve_booking(request, booking_id):

    booking = get_object_or_404(Booking, id=booking_id)

    if booking.status != 'pending':
        messages.error(request, 'This booking cannot be approved.')
        return redirect('admin_bookings')

    booking.status = 'approved'
    booking.save(update_fields=['status'])

    messages.success(request, 'Booking approved successfully.')

    return redirect('admin_bookings')

@login_required
@user_passes_test(lambda user: user.is_staff, login_url='login')
@require_POST
def reject_booking(request, booking_id):

    booking = get_object_or_404(Booking, id=booking_id)

    if booking.status != 'pending':
        messages.error(request, 'This booking cannot be rejected.')
        return redirect('admin_bookings')

    booking.status = 'rejected'
    booking.save(update_fields=['status'])

    messages.success(request, 'Booking rejected successfully.')

    return redirect('admin_bookings')

@login_required
@user_passes_test(lambda user: user.is_staff, login_url='login')
@require_POST
def allocate_room(request, booking_id):

    allocation_date = parse_date(
        request.POST.get('allocation_date', '')
    )

    room_id = request.POST.get('room_id')

    if not allocation_date:
        messages.error(request, 'Please select a valid allocation date.')
        return redirect('admin_bookings')

    if allocation_date < timezone.localdate():
        messages.error(request, 'Allocation date cannot be in the past.')
        return redirect('admin_bookings')

    with transaction.atomic():

        booking = get_object_or_404(
            Booking.objects.select_for_update(),
            id=booking_id
        )

        if booking.status != 'approved' or booking.room_id is not None:
            messages.error(
                request,
                'This booking is not eligible for room allocation.'
            )
            return redirect('admin_bookings')

        room = get_object_or_404(
            Room.objects.select_for_update(),
            id=room_id,
            is_active=True
        )

        if room.room_type != booking.requested_room_type:
            messages.error(
                request,
                'Please select a room matching the requested room type.'
            )
            return redirect('admin_bookings')

        occupied_beds = Booking.objects.filter(
            room=room,
            status='approved',
            allocated_date__lte=allocation_date
        ).filter(
            Q(vacated_date__isnull=True) |
            Q(vacated_date__gt=allocation_date)
        ).count()

        if occupied_beds >= room.capacity:
            messages.error(
                request,
                'This room has no available beds on the selected date.'
            )
            return redirect('admin_bookings')

        booking.room = room
        booking.allocated_date = allocation_date
        booking.monthly_rate_at_allocation = room.monthly_rate
        booking.save()

    messages.success(
        request,
        f'Room {room.room_number} allocated successfully.'
    )

    return redirect('admin_bookings')


@login_required
@user_passes_test(lambda user: user.is_staff, login_url='login')
@require_POST
def complete_booking(request, booking_id):

    booking = get_object_or_404(Booking, id=booking_id)

    today = timezone.localdate()

    if booking.status != 'approved' or not booking.room:
        messages.error(
            request,
            'This booking cannot be completed.'
        )
        return redirect('admin_bookings')

    if not booking.allocated_date or booking.allocated_date > today:
        messages.error(
            request,
            'This student has not started their accommodation yet.'
        )
        return redirect('admin_bookings')

    booking.status = 'completed'
    booking.vacated_date = today

    booking.save(update_fields=['status', 'vacated_date'])

    messages.success(
        request,
        f'Booking for {booking.student.user.username} completed successfully.'
    )

    return redirect('admin_bookings')