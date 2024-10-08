from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta, datetime
from django.core.exceptions import ValidationError
from.credentials import *
from django.contrib import messages
import stripe
from django.urls import reverse
from.decorators import *
from .utilis import *
from django.utils.safestring import mark_safe
from users.models import User
from.forms import *
import pandas as pd
import os
from django.conf import settings
from django.template.loader import render_to_string
from django.db.models import Sum, Count
from django.utils.dateparse import parse_datetime
from django.db.models import F, Sum, Count



def gamerz_view(request):
    return render(request, 'gamerz/gamer.html')

@login_required
def game_list_view(request):
    games = Game.objects.all()
    return render(request, 'gamerz/game_list.html', {'games': games})

def game_detail_view(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    return render(request, 'gamerz/game_detail.html', {'game': game})

def favorite_game_view(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    user = request.user
    if game in user.favorite_games.all():
        user.favorite_games.remove(game)
    else:
        user.favorite_games.add(game)
    return redirect('game_detail', game_id=game_id)

@login_required
def favorite_games_list_view(request):
    user = request.user
    favorite_games = user.favorite_games.all()
    return render(request, 'gamerz/favorite_games_list.html', {'favorite_games': favorite_games})



def add_favorite(request, pk):
    game = get_object_or_404(Game, pk=pk)
    request.user.favorite_games.add(game)
    return redirect('game_list')

def remove_favorite(request, pk):
    game = get_object_or_404(Game, pk=pk)
    request.user.favorite_games.remove(game)
    return redirect('game_list')

#def game_reservations(request):
#    # Implement game reservations view here
#    pass

#def leaderboards(request):
    # Implement leaderboards view here
    pass
def ongoing_game_detail(request, pk):
    game = get_object_or_404(OngoingGame, pk=pk)
    context = {
        'game': game,
    }
    return render(request, 'gamerz/ongoing_game_detail.html', context)


def gameform(request):
    return render(request, 'gamerz/game_form.html')


def reservation_view(request):
    stations = GamingStation.objects.all()
    if request.method == 'POST':
        station_id = request.POST.get('station_id')
        start_time_str = request.POST.get('start_time')
        duration = int(request.POST.get('duration'))

        # Parse start time and calculate end time
        start_time = parse_datetime(start_time_str)
        end_time = start_time + timedelta(hours=duration)

        # Get the selected station
        station = GamingStation.objects.get(id=station_id)

        # Check for overlapping reservations
        overlapping_reservations = Reservation.objects.filter(
            station=station,
            end_time__gt=start_time,
            start_time__lt=end_time
        )

        if overlapping_reservations.exists():
            messages.error(request, 'The selected station is already reserved for the specified time period.')
            return render(request, 'gamerz/reservation.html', {'stations': stations})

        # Create and save the new reservation
        reservation = Reservation(
            user=request.user,
            station=station,
            start_time=start_time,
            end_time=end_time,
        )
        reservation.save()

        return redirect('payments', reservation_id=reservation.id)

    return render(request, 'gamerz/reservation.html', {'stations': stations})


def reservation_list_view(request):
    reservations = Reservation.objects.filter(user=request.user)
    reservation_data = []

    for reservation in reservations:
        # Calculate the total hours
        total_hours = (reservation.end_time - reservation.start_time).total_seconds() / 3600
        # Calculate the total cost
        total_cost = total_hours * 200  # Ksh 200 per hour

        # Store the data in a dictionary
        reservation_data.append({
            'station_name': reservation.station.name,
            'start_time': reservation.start_time,
            'end_time': reservation.end_time,
            'total_hours': total_hours,
            'total_cost': total_cost
        })

    return render(request, 'gamerz/reservation_list.html', {'reservation_data': reservation_data})


def leaderboard_view(request):
    scores = GamerScore.objects.order_by('-score')[:10]
    return render(request, 'gamerz/leaderboard.html', {'scores': scores})

def achievement_view(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    achievements = Achievement.objects.filter(game=game)
    return render(request, 'gamerz/achievement.html', {'game': game, 'achievements': achievements})


def chat_room_view(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)
    return render(request, 'chat/chat_room.html', {'room': room})

def get_messages(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)
    messages = room.messages.order_by('-timestamp')[:50]  # Get the last 50 messages
    messages = reversed(messages)  # Reverse them to show the most recent at the bottom
    return JsonResponse([{'user': message.user.username, 'content': message.content, 'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S')} for message in messages], safe=False)

@csrf_exempt
def send_message(request, room_id):
    if request.method == "POST":
        room = get_object_or_404(ChatRoom, id=room_id)
        content = request.POST.get('content')
        message = Message.objects.create(room=room, user=request.user, content=content)
        return JsonResponse({'user': message.user.username, 'content': message.content, 'timestamp': message.timestamp.strftime('%Y-%m-%d %H:%M:%S')})


def shop_location_view(request):
    return render(request, 'gamerz/shop_location.html')


def payments_view(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    return render(request, 'gamerz/payments.html', {'reservation': reservation})

def mpesa_view(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)

    # Calculate the total hours and cost for the reservation
    total_hours = (reservation.end_time - reservation.start_time).total_seconds() / 3600
    total_cost = total_hours * 200  # Ksh 200 per hour

    reservation_data = {
        'station_name': reservation.station.name,
        'start_time': reservation.start_time,
        'end_time': reservation.end_time,
        'total_hours': total_hours,
        'total_cost': total_cost
    }

    if request.method == 'POST':
        phone = request.POST['phone']
        amount = total_cost
        access_token = MpesaAccessToken.validated_mpesa_access_token
        api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        headers = {"Authorization": "Bearer %s" % access_token}
        payment_request = {
            "BusinessShortCode": LipanaMpesaPassword.Business_short_code,
            "Password": LipanaMpesaPassword.decode_password,
            "Timestamp": LipanaMpesaPassword.lipa_time,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": LipanaMpesaPassword.Business_short_code,
            "PhoneNumber": phone,
            "CallBackURL": "https://sandbox.safaricom.co.ke/mpesa/",
            "AccountReference": "PYMENT001",
            "TransactionDesc": "Gaming Station Reservation"
        }

        response = requests.post(api_url, json=payment_request, headers=headers)
        
        # Print the response for debugging
        print("Response Status Code:", response.status_code)
        print("Response Text:", response.text)

        if response.status_code == 200:
            # Payment initiated successfully
            messages.success(request, "Payment initiated successfully. Please complete your payment via Mpesa.")
            return redirect('reservation_list')
        else:
            # Handle payment failure or errors here
            messages.error(request, f"Payment initiation failed. Error: {response.text}")
            return redirect('home')

    return render(request, 'gamerz/mpesa.html', {'reservation_data': reservation_data})



def paypal_view(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)

    # Calculate the total hours and cost for the reservation
    total_hours = (reservation.end_time - reservation.start_time).total_seconds() / 3600
    total_cost = total_hours * 200  # Ksh 200 per hour

    reservation_data = {
        'station_name': reservation.station.name,
        'start_time': reservation.start_time,
        'end_time': reservation.end_time,
        'total_hours': total_hours,
        'total_cost': total_cost
    }

    if request.method == 'POST':
        
        return redirect('home')

    return render(request, 'gamerz/paypal.html', {'reservation_data': reservation_data})



def payment_success(request):
    if request.method == 'POST':
        # Handle any necessary logic here
        messages.success(request, "Payment completed successfully!")
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)



def stripe_view(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)

    # Calculate the total hours and cost for the reservation
    total_hours = (reservation.end_time - reservation.start_time).total_seconds() / 3600
    total_cost = total_hours * 200  # Ksh 200 per hour

    reservation_data = {
        'station_name': reservation.station.name,
        'start_time': reservation.start_time,
        'end_time': reservation.end_time,
        'total_hours': total_hours,
        'total_cost': total_cost,
        'reservation': reservation,  # Pass the reservation object
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY
    }

    return render(request, 'gamerz/stripe.html', {'reservation_data': reservation_data})


stripe.api_key = settings.STRIPE_SECRET_KEY


def create_checkout_session(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, user=request.user)
    
    total_hours = (reservation.end_time - reservation.start_time).total_seconds() / 3600
    total_cost = int(total_hours * 200)  # Convert to integer (Ksh 200 per hour)
    
    print("Creating Stripe Checkout Session...")
    
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',  # Stripe expects currency in lowercase
                'product_data': {
                    'name': f'Reservation for {reservation.station.name}',
                },
                'unit_amount': total_cost * 100,  # Stripe expects amount in cents
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri(reverse('reservation_success')),
        cancel_url=request.build_absolute_uri(reverse('reservation_cancel')),
    )

    print("Stripe Checkout Session created:", session.id)
    
    return JsonResponse({
        'id': session.id
    })


def reservation_success(request):
    messages.success(request, "Payment completed successfully!")
    return render(request, 'gamerz/reservation_success.html')

def reservation_cancel(request):
    messages.error(request, "Payment was canceled.")
    return render(request, 'gamerz/reservation_cancel.html')



def event_list(request):
    events = Event.objects.filter(status='Scheduled').order_by('start_date')
    return render(request, 'gamerz/event_list.html', {'events': events})

@login_required
def register_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if Registration.objects.filter(event=event, user=request.user).exists():
        # User already registered
        return redirect('event_list')
    
    if event.max_participants and Registration.objects.filter(event=event).count() >= event.max_participants:
        # Event is full
        return redirect('event_list')
    
    # Check if the event has a registration fee
    if event.registration_fee > 0:
        # Redirect to payment gateway (e.g., Stripe, PayPal) for processing
        return redirect('payment_tournament', event_id=event.id)

    registration = Registration.objects.create(event=event, user=request.user, status='Registered')
    return redirect('event_list')

def payment_tournament(request, event_id):
    tournament = get_object_or_404(Event, id=event_id)
    return render(request, 'gamerz/tournamentpay.html', {'tournament': tournament})

@login_required
def my_events(request):
    registrations = Registration.objects.filter(user=request.user)
    return render(request, 'gamerz/my_events.html', {'registrations': registrations})



def get_weather_data(nairobi):
    api_key = 'dcdde97a40e173829aaeabf6c422e001'
    api_url = f'http://api.openweathermap.org/data/2.5/weather?q={nairobi}&units=metric&appid={api_key}'
    response = requests.get(api_url)
    if response.status_code == 200:
        print(f"Weather API response for {nairobi}: {response.json()}")
        return response.json()
    else:
        print(f"Failed to fetch weather data for {nairobi}: {response.status_code}")
        return None


def event_calendar(request):
    events = Event.objects.filter(status='Scheduled')

    event_data = []
    
    for event in events:
        weather_data = get_weather_data(event.city_name) if event.city_name else None
        event_info = {
            'title': event.name,
            'start': event.start_date.isoformat(),
            'end': event.end_date.isoformat(),
            'city_name': event.city_name,
            'weather': weather_data['weather'][0]['description'] if weather_data else 'N/A',
            'temperature': weather_data['main']['temp'] if weather_data else 'N/A',
        }
        print(f"Processed Event Data: {event_info}")
        event_data.append(event_info)

    event_data_json = mark_safe(json.dumps(event_data))
    return render(request, 'gamerz/event_calendar.html', {'events': event_data_json})




def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, 'gamerz/event_detail.html', {'event': event})


def tournament_mpesa(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    total_cost = float(event.registration_fee)
    registration, created = Registration.objects.get_or_create(event=event, user=request.user)

    if not created:  # If registration already exists
        if registration.payment_status == 'Pending':
            messages.warning(request, "Payment already initiated. Please complete the payment via Mpesa.")
            return redirect('event_list')
        elif registration.payment_status == 'Paid':
            messages.info(request, "You have already paid for this tournament.")
            return redirect('event_list')

    if request.method == 'POST':
        phone = request.POST['phone']
        amount = total_cost
        access_token = MpesaAccessToken.validated_mpesa_access_token
        api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        headers = {"Authorization": "Bearer %s" % access_token}
        payment_request = {
            "BusinessShortCode": LipanaMpesaPassword.Business_short_code,
            "Password": LipanaMpesaPassword.decode_password,
            "Timestamp": LipanaMpesaPassword.lipa_time,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": LipanaMpesaPassword.Business_short_code,
            "PhoneNumber": phone,
            "CallBackURL": "https://sandbox.safaricom.co.ke/mpesa/",
            "AccountReference": "PYMENT001",
            "TransactionDesc": "Tournament Fee Registration"
        }

        response = requests.post(api_url, json=payment_request, headers=headers)
        
        # Print the response for debugging
        print("Response Status Code:", response.status_code)
        print("Response Text:", response.text)

        if response.status_code == 200:
            # Payment initiated successfully
            messages.success(request, "Payment initiated successfully. Please complete your payment via Mpesa.")
            return redirect('reservation_list')
        else:
            # Handle payment failure or errors here
            messages.error(request, f"Payment initiation failed. Error: {response.text}")
            return redirect('home')

    return render(request, 'gamerz/tournament_mpesa.html', {'event': event})



def tournament_paypal(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, 'gamerz/tournament_paypal.html', {'event': event})


def select_membership(request):
    plans = MembershipPlan.objects.all()
    return render(request, 'gamerz/select_membership.html', {'plans': plans})


def calculate_end_date(duration_days):
    return timezone.now() + timedelta(days=duration_days)


@login_required
def subscribe(request, plan_id):
    plan = get_object_or_404(MembershipPlan, id=plan_id)
    if request.method == 'POST':
        # Here you would handle the payment process
        # After successful payment:
        Membership.objects.update_or_create(
            user=request.user,
            defaults={'tier': plan.name, 'end_date': calculate_end_date(plan.duration_days), 'is_active': True}
        )
        return redirect('membership_payment_page', plan_id=plan.id)
    return render(request, 'gamerz/subscribe.html', {'plan': plan})


def payment_membership(request, plan_id):
    plan = get_object_or_404(MembershipPlan, id=plan_id)
    return render(request, 'gamerz/membershippay.html', {'plan': plan})

def membershipmpesa(request, plan_id):
    plan = get_object_or_404(MembershipPlan, id=plan_id)
    print(plan)  # Debugging

    if request.method == 'POST':
        phone = request.POST['phone']
        amount = float(plan.price)  # Correctly access the plan's price
        access_token = MpesaAccessToken.validated_mpesa_access_token
        api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        headers = {"Authorization": "Bearer %s" % access_token}
        payment_request = {
            "BusinessShortCode": LipanaMpesaPassword.Business_short_code,
            "Password": LipanaMpesaPassword.decode_password,
            "Timestamp": LipanaMpesaPassword.lipa_time,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": LipanaMpesaPassword.Business_short_code,
            "PhoneNumber": phone,
            "CallBackURL": "https://sandbox.safaricom.co.ke/mpesa/",
            "AccountReference": "PAYMENT001",
            "TransactionDesc": "Membership Fee"
        }

        response = requests.post(api_url, json=payment_request, headers=headers)
        
        # Debugging response
        print("Response Status Code:", response.status_code)
        print("Response Text:", response.text)

        if response.status_code == 200:
            messages.success(request, "Payment initiated successfully. Please complete your payment via Mpesa.")
            return redirect('membership_success')  # Change to an appropriate redirect
        else:
            messages.error(request, f"Payment initiation failed. Error: {response.text}")
            return redirect('home')  # Change to an appropriate redirect

    return render(request, 'gamerz/membershipmpesa.html', {'plan': plan})


def membershippaypal(request, plan_id):
    plan = get_object_or_404(MembershipPlan, id=plan_id)
    return render(request, 'gamerz/membershippaypal.html', {'plan': plan})


@login_required
def manage_membership(request):
    membership = Membership.objects.get(user=request.user)
    return render(request, 'gamerz/manage_membership.html', {'membership': membership})


def membership_success(request):
    return render(request, 'gamerz/membership_success.html')


def select_membership(request):
    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        plan = get_object_or_404(MembershipPlan, id=plan_id)
        membership, created = Membership.objects.get_or_create(user=request.user)
        
        if membership.is_active:
            # Update membership tier and extend end date based on the new plan
            membership.tier = plan.name
            membership.end_date = timezone.now() + timedelta(days=plan.duration_days)
            membership.save()
            messages.success(request, "Your membership has been upgraded.")
        else:
            # Create a new membership
            membership = Membership.objects.create(
                user=request.user,
                tier=plan.name,
                start_date=timezone.now(),
                end_date=timezone.now() + timedelta(days=plan.duration_days),
                is_active=True
            )
            messages.success(request, "You have successfully subscribed to the new membership plan.")
        
        # Pass the selected plan's name to the success page
        return render(request, 'gamerz/subscription_success.html', {'plan_name': plan.name})

    plans = MembershipPlan.objects.all()
    return render(request, 'gamerz/select_membership.html', {'plans': plans})

def cancel_membership(request):
    membership = request.user.membership
    if membership:
        membership.is_active = False  # Mark the membership as inactive
        membership.save()
        messages.success(request, "Your membership has been canceled.")
    else:
        messages.error(request, "No active membership found.")
    
    return redirect('managemembership')


@membership_required('Basic')
def exclusive_content(request):
    # Your view logic here
    return render(request, 'exclusive/basic.html')

@membership_required('Premium')
def exclusive_content(request):
    # Your view logic here
    return render(request, 'exclusive/premium.html')

@membership_required('Elite')
def exclusive_content(request):
    # Your view logic here
    return render(request, 'exclusive/elite.html')


def event_weather(request, city_name):
    weather_data = get_weather_data(city_name)
    return render(request, 'gamerz/event_weather.html', {'weather_data': weather_data, 'city_name': city_name})


#ef twitch_streams_view(request):
#   game_name = request.GET.get('game', 'Fortnite')  # Default to 'Fortnite'
#   streams = get_twitch_streams(game_name)
#   return render(request, 'gamerz/twitch_streams.html', {'streams': streams})




#def get_oauth_token(client_id, client_secret):
#    url = 'https://id.twitch.tv/oauth2/token'
#    params = {
#        'client_id': client_id,
#        'client_secret': client_secret,
#        'grant_type': 'client_credentials',
#    }
#    response = requests.post(url, params=params)
#    return response.json()
#
#def get_oauth_token_view(request):
#    # Replace with your actual Client ID and Client Secret
#    client_id = 'by462onfaxsc3ynv8b951ako0o1n99'
#    client_secret = '3vmdqjd5m9wtd1u9lhqwb9byq2qcdv'
#    
#    # Call the function with the correct arguments
#    token_response = get_oauth_token(client_id, client_secret)
#    
#    return JsonResponse(token_response)

#CLIENT_ID = 'by462onfaxsc3ynv8b951ako0o1n99'
#CLIENT_SECRET = '3vmdqjd5m9wtd1u9lhqwb9byq2qcdv'
#{"access_token": "fprqxxzaxmnbj6hlq0q3lpg2xvsckd", "expires_in": 5003716, "token_type": "bearer"}

#def get_twitch_streams(game_name):
#    client_id = 'by462onfaxsc3ynv8b951ako0o1n99'
#    oauth_token = 'fprqxxzaxmnbj6hlq0q3lpg2xvsckd'
#    headers = {
#        'Client-ID': client_id,
#        'Authorization': f'Bearer {oauth_token}',
#    }
#    url = f'https://api.twitch.tv/helix/streams?game_name={game_name}'
#    response = requests.get(url, headers=headers)
#    return response.json().get('data', [])
#
#def twitch_streams_view(request):
#    return render(request, 'gamerz/twitch_streams.html')

#Employee Views
def employee_reservation_view(request):
    reservations = Reservation.objects.all().select_related('user', 'station')
    reservation_data = []

    for reservation in reservations:
        # Calculate the total hours
        total_hours = (reservation.end_time - reservation.start_time).total_seconds() / 3600
        # Calculate the total cost
        total_cost = total_hours * 200  # Ksh 200 per hour

        # Store the data in a dictionary
        reservation_data.append({
            'reservation_id': reservation.id,
            'user_username': reservation.user.username,
            'station_name': reservation.station.name,
            'start_time': reservation.start_time,
            'end_time': reservation.end_time,
            'total_hours': total_hours,
            'total_cost': total_cost
        })

    return render(request, 'employee/reservation_list.html', {'reservation_data': reservation_data})


def achievements_by_gamers_view(request):
    # Retrieve all achievements and associated gamer scores
    achievements = Achievement.objects.all()
    gamers_scores = GamerScore.objects.select_related('user').prefetch_related('achievements').all()

    # Prepare a dictionary to store gamer achievements
    gamer_achievements = {}
    for gamer_score in gamers_scores:
        if gamer_score.user not in gamer_achievements:
            gamer_achievements[gamer_score.user] = {
                'score': gamer_score.score,
                'achievements': list(gamer_score.achievements.all())
            }

    # Rank gamers based on their scores
    sorted_gamers = sorted(gamer_achievements.items(), key=lambda item: item[1]['score'], reverse=True)
    ranked_gamers = {user: {**info, 'rank': index + 1} for index, (user, info) in enumerate(sorted_gamers)}

    return render(request, 'employee/achievements_by_gamers.html', {
        'achievements': achievements,
        'gamer_achievements': ranked_gamers
    })

def monitor_games_view(request):
    # Retrieve all gaming stations
    stations = GamingStation.objects.all()

    # Update each station's availability based on active ongoing games
    for station in stations:
        # Check if there's any active ongoing game for this station
        active_games = OngoingGame.objects.filter(station=station, status='Active')
        
        # If there's an active game, set is_occupied to True; otherwise, False
        if active_games.exists():
            station.is_occupied = True
        else:
            station.is_occupied = False
        
        # Save the updated status to the database
        station.save()

    # Retrieve all ongoing games
    ongoing_games = OngoingGame.objects.all()

    return render(request, 'employee/monitorgames.html', {
        'ongoing_games': ongoing_games,
        'stations': stations,
    })


def employee_manage_gamers_view(request):
    gamers = User.objects.all()  # Fetch all gamers
    return render(request, 'employee/manage_gamers.html', {'gamers': gamers})

def gamer_detail_view(request, user_id):
    gamer = get_object_or_404(User, id=user_id)
    return render(request, 'employee/gamer_detail.html', {'gamer': gamer})

def update_gamer_view(request, user_id):
    gamer = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        gamer.username = request.POST.get('username')
        gamer.email = request.POST.get('email')
        # Update other fields as needed
        gamer.save()
        messages.success(request, 'Gamer details updated successfully')
        return redirect('adminmanagegamers')
    return render(request, 'employee/update_gamer.html', {'gamer': gamer})

def delete_gamer_view(request, game_id):
    gamer = get_object_or_404(Game, id=game_id)
    if request.method == 'POST':
        gamer.delete()
        return redirect('adminmanagegamers')
    return redirect('adminmanagegamers')

def employee_settings_view(request):
    return render(request, 'employee/settings.html')


def create_event_view(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            return redirect('manageevents')  # Redirect to a list of events or another relevant page
    else:
        form = EventForm()
    
    return render(request, 'employee/create_event.html', {'form': form})

def manage_events_view(request):
    events = Event.objects.all().order_by('start_date')
    return render(request, 'employee/manage_events.html', {'events': events})


def edit_event_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            return redirect('manageevents')  # Redirect to the event management page
        else:
            print(form.errors)  # Print form errors to console for debugging
    else:
        form = EventForm(instance=event)
    return render(request, 'employee/edit_event.html', {'form': form, 'event': event})

#def delete_event_view(request, event_id):
#    event = get_object_or_404(Event, id=event_id)
#    if request.method == 'POST':
#        event.delete()
#        return redirect('manageevents')
#    return redirect('manageevents')


def employee_report_view(request):
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            form.save()  # Save the new sale entry
            
            # Prepare the updated sales data for AJAX response
            sales_data = Sale.objects.values('date').annotate(
                total_sales=Sum('total_sales'),
                total_clients=Count('client', distinct=True)
            ).order_by('date')
            
            # Prepare the updated chart data
            chart_data = {
                'dates': [sale['date'].strftime('%Y-%m-%d') for sale in sales_data],
                'total_sales': [sale['total_sales'] for sale in sales_data],
            }
            
            html_sales_table = render_to_string('employee/report.html', {'sales_data': sales_data})
            return JsonResponse({'html_sales_table': html_sales_table})
        else:
            # Return form errors if the form is invalid
            return JsonResponse({'errors': form.errors}, status=400)
    else:
        form = SaleForm()
    
    # Retrieve aggregated sales data grouped by date
    sales_data = Sale.objects.values('date').annotate(
        total_sales=Sum('total_sales'),
        total_clients=Count('client', distinct=True)
    ).order_by('date')
    
    # Retrieve list of clients for the dropdown
    clients = Client.objects.all()
    
    # Prepare chart data
    chart_data = {
        'dates': [sale['date'].strftime('%Y-%m-%d') for sale in sales_data],
        'total_sales': [sale['total_sales'] for sale in sales_data],
    }

    return render(request, 'employee/report.html', {
        'form': form,
        'sales_data': sales_data,
        'chart_data': chart_data,
        'clients': clients,  # Pass clients to the template
    })
    

def chart_view(request):
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            form.save()  # Save the new sale entry

            # Prepare the updated sales data for AJAX response
            sales_data = Sale.objects.values('date').annotate(
                total_sales=Sum('total_sales'),
                total_clients=Count('client', distinct=True)
            ).order_by('date')

            # Handle AJAX response if needed
            # return JsonResponse({'some_key': some_value})

        else:
            # Return form errors if the form is invalid
            return JsonResponse({'errors': form.errors}, status=400)
    else:
        form = SaleForm()

    # Retrieve aggregated sales data grouped by date
    sales_data = Sale.objects.values('date').annotate(
        total_sales=Sum('total_sales'),
        total_clients=Count('client', distinct=True)
    ).order_by('date')

    # Retrieve sales data from events grouped by date
    event_sales_data = Event.objects.values('start_date').annotate(
        total_event_sales=Sum('registration_fee')
    ).order_by('start_date')

    # Retrieve sales data from memberships grouped by date
    membership_sales_data = Membership.objects.values('created_at__date').annotate(
        total_membership_sales=Sum('plan__price')  # Access price via ForeignKey
    ).order_by('created_at__date')

    # Retrieve reservation data grouped by date
    reservation_data = Reservation.objects.values('start_time__date').annotate(
        count=Count('id')
    ).order_by('start_time__date')

    # Prepare chart data
    chart_data = {
        'daily_sales_dates': [sale['date'].strftime('%Y-%m-%d') for sale in sales_data],
        'daily_sales_amount': [float(sale['total_sales']) if sale['total_sales'] is not None else 0 for sale in sales_data],
        'reservation_dates': [res['start_time__date'].strftime('%Y-%m-%d') for res in reservation_data],
        'total_reservations': [res['count'] for res in reservation_data],
        'dates': [sale['date'].strftime('%Y-%m-%d') for sale in sales_data],
        'total_sales': [float(sale['total_sales']) if sale['total_sales'] is not None else 0 for sale in sales_data],
        'event_sales_dates': [event['start_date'].strftime('%Y-%m-%d') for event in event_sales_data],
        'total_event_sales': [float(event['total_event_sales']) if event['total_event_sales'] is not None else 0 for event in event_sales_data],
        'membership_sales_dates': [membership['created_at__date'].strftime('%Y-%m-%d') for membership in membership_sales_data],
        'total_membership_sales': [float(membership['total_membership_sales']) if membership['total_membership_sales'] is not None else 0 for membership in membership_sales_data],
    }
    print(sales_data)
    print(event_sales_data)
    print(membership_sales_data)
    print(reservation_data)


    return render(request, 'employee/chart.html', {
        'form': form,
        'sales_data': sales_data,
        'chart_data': chart_data,
    })


def admin_manage_gamers_view(request):
    gamers = User.objects.all() 
    return render(request, 'admin/admin_manage_gamers.html', {'gamers': gamers})

def admin_monitor_games_view(request):
    # Retrieve all gaming stations
    stations = GamingStation.objects.all()

    # Update each station's availability based on active ongoing games
    for station in stations:
        # Check if there's any active ongoing game for this station
        active_games = OngoingGame.objects.filter(station=station, status='Active')
        
        # If there's an active game, set is_occupied to True; otherwise, False
        if active_games.exists():
            station.is_occupied = True
        else:
            station.is_occupied = False
        
        # Save the updated status to the database
        station.save()

    # Retrieve all ongoing games
    ongoing_games = OngoingGame.objects.all()

    return render(request, 'admin/adminmonitorgames.html', {
        'ongoing_games': ongoing_games,
        'stations': stations,
    })

def admin_reservation_view(request):
    reservations = Reservation.objects.all().select_related('user', 'station')
    reservation_data = []

    for reservation in reservations:
        # Calculate the total hours
        total_hours = (reservation.end_time - reservation.start_time).total_seconds() / 3600
        # Calculate the total cost
        total_cost = total_hours * 200  # Ksh 200 per hour

        # Store the data in a dictionary
        reservation_data.append({
            'reservation_id': reservation.id,
            'user_username': reservation.user.username,
            'station_name': reservation.station.name,
            'start_time': reservation.start_time,
            'end_time': reservation.end_time,
            'total_hours': total_hours,
            'total_cost': total_cost
        })

    return render(request, 'admin/admin_reservation_list.html', {'reservation_data': reservation_data})

def delete_reservation_view(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    reservation.delete()
    messages.success(request, "Reservation successfully deleted.")
    return redirect('adminreservation')

def admin_achievements_by_gamers_view(request):
    # Retrieve all achievements and associated gamer scores
    achievements = Achievement.objects.all()
    gamers_scores = GamerScore.objects.select_related('user').prefetch_related('achievements').all()

    # Prepare a dictionary to store gamer achievements
    gamer_achievements = {}
    for gamer_score in gamers_scores:
        if gamer_score.user not in gamer_achievements:
            gamer_achievements[gamer_score.user] = {
                'score': gamer_score.score,
                'achievements': list(gamer_score.achievements.all())
            }

    # Rank gamers based on their scores
    sorted_gamers = sorted(gamer_achievements.items(), key=lambda item: item[1]['score'], reverse=True)
    ranked_gamers = {user: {**info, 'rank': index + 1} for index, (user, info) in enumerate(sorted_gamers)}

    return render(request, 'admin/admin_achievements_by_gamers.html', {
        'achievements': achievements,
        'gamer_achievements': ranked_gamers
    })

def admin_manage_events_view(request):
    events = Event.objects.all().order_by('start_date')
    return render(request, 'admin/admin_manage_events.html', {'events': events})

def delete_event_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    event.delete()
    messages.success(request, "Event successfully deleted.")
    return redirect('adminmanageevents')


def edit_event_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == "POST":
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, "Event successfully updated.")
            return redirect('adminmanageevents')
    else:
        form = EventForm(instance=event)
    return render(request, 'admin/edit_event.html', {'form': form})

def admin_report_view(request):
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            form.save()  # Save the new sale entry
            
            # Prepare the updated sales data for AJAX response
            sales_data = Sale.objects.values('date').annotate(
                total_sales=Sum('total_sales'),
                total_clients=Count('client', distinct=True)
            ).order_by('date')
            
            # Prepare the updated chart data
            chart_data = {
                'dates': [sale['date'].strftime('%Y-%m-%d') for sale in sales_data],
                'total_sales': [sale['total_sales'] for sale in sales_data],
            }
            
            html_sales_table = render_to_string('employee/report.html', {'sales_data': sales_data})
            return JsonResponse({'html_sales_table': html_sales_table})
        else:
            # Return form errors if the form is invalid
            return JsonResponse({'errors': form.errors}, status=400)
    else:
        form = SaleForm()
    
    # Retrieve aggregated sales data grouped by date
    sales_data = Sale.objects.values('date').annotate(
        total_sales=Sum('total_sales'),
        total_clients=Count('client', distinct=True)
    ).order_by('date')
    
    # Retrieve list of clients for the dropdown
    clients = Client.objects.all()
    
    # Prepare chart data
    chart_data = {
        'dates': [sale['date'].strftime('%Y-%m-%d') for sale in sales_data],
        'total_sales': [sale['total_sales'] for sale in sales_data],
    }

    return render(request, 'admin/admin_report.html', {
        'form': form,
        'sales_data': sales_data,
        'chart_data': chart_data,
        'clients': clients,  # Pass clients to the template
    })

def admin_chart_view(request):
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            form.save()  # Save the new sale entry

            # Prepare the updated sales data for AJAX response
            sales_data = Sale.objects.values('date').annotate(
                total_sales=Sum('total_sales'),
                total_clients=Count('client', distinct=True)
            ).order_by('date')

            # Handle AJAX response if needed
            # return JsonResponse({'some_key': some_value})

        else:
            # Return form errors if the form is invalid
            return JsonResponse({'errors': form.errors}, status=400)
    else:
        form = SaleForm()

    # Retrieve aggregated sales data grouped by date
    sales_data = Sale.objects.values('date').annotate(
        total_sales=Sum('total_sales'),
        total_clients=Count('client', distinct=True)
    ).order_by('date')

    # Retrieve sales data from events grouped by date
    event_sales_data = Event.objects.values('start_date').annotate(
        total_event_sales=Sum('registration_fee')
    ).order_by('start_date')

    # Retrieve sales data from memberships grouped by date
    membership_sales_data = Membership.objects.values('created_at__date').annotate(
        total_membership_sales=Sum('plan__price')  # Access price via ForeignKey
    ).order_by('created_at__date')

    # Retrieve reservation data grouped by date
    reservation_data = Reservation.objects.values('start_time__date').annotate(
        count=Count('id')
    ).order_by('start_time__date')

    # Prepare chart data
    chart_data = {
        'daily_sales_dates': [sale['date'].strftime('%Y-%m-%d') for sale in sales_data],
        'daily_sales_amount': [float(sale['total_sales']) if sale['total_sales'] is not None else 0 for sale in sales_data],
        'reservation_dates': [res['start_time__date'].strftime('%Y-%m-%d') for res in reservation_data],
        'total_reservations': [res['count'] for res in reservation_data],
        'dates': [sale['date'].strftime('%Y-%m-%d') for sale in sales_data],
        'total_sales': [float(sale['total_sales']) if sale['total_sales'] is not None else 0 for sale in sales_data],
        'event_sales_dates': [event['start_date'].strftime('%Y-%m-%d') for event in event_sales_data],
        'total_event_sales': [float(event['total_event_sales']) if event['total_event_sales'] is not None else 0 for event in event_sales_data],
        'membership_sales_dates': [membership['created_at__date'].strftime('%Y-%m-%d') for membership in membership_sales_data],
        'total_membership_sales': [float(membership['total_membership_sales']) if membership['total_membership_sales'] is not None else 0 for membership in membership_sales_data],
    }


    return render(request, 'admin/admin_chart.html', {
        'form': form,
        'sales_data': sales_data,
        'chart_data': chart_data,
    })

def admin_create_event_view(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            return redirect('adminmanageevents') 
    else:
        form = EventForm()
    
    return render(request, 'admin/admin_create_event.html', {'form': form})
