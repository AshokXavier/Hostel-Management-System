
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from hostel.models import Room


class Command(BaseCommand):
    help = 'Create the 20 predefined hostel rooms'

    def get_rate(self, room_type):
        while True:
            value = input(
                f"Enter monthly rate for {room_type} rooms: "
            )

            try:
                rate = Decimal(value)

                if rate < 0:
                    print("Rate cannot be negative.")
                    continue

                if rate.as_tuple().exponent < -2:
                    print("Please enter a maximum of 2 decimal places.")
                    continue

                if rate > Decimal("999999.99"):
                    print("Rate exceeds the allowed maximum.")
                    continue

                return rate

            except InvalidOperation:
                print("Please enter a valid amount.")

    def handle(self, *args, **kwargs):

        dormitory_rate = self.get_rate("Dormitory")
        twin_rate = self.get_rate("Twin Bed")

        created_count = 0
        existing_count = 0

        with transaction.atomic():

            for room_number in range(1, 21):

                if room_number <= 10:
                    room_type = 'dormitory'
                    monthly_rate = dormitory_rate
                else:
                    room_type = 'twin'
                    monthly_rate = twin_rate

                room, created = Room.objects.get_or_create(
                    room_number=str(room_number),
                    defaults={
                        'room_type': room_type,
                        'monthly_rate': monthly_rate,
                        'facilities': '',
                        'is_active': True,
                    }
                )

                if created:
                    created_count += 1
                else:
                    existing_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {created_count} rooms."
            )
        )

        self.stdout.write(
            f"Already existing rooms: {existing_count}"
        )
