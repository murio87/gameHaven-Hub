from django.urls import path
from. import views


urlpatterns = [
    path('gamerz/', views.gamerz_view, name='gamerz'),
    path('games/', views.game_list_view, name='game_list'),
    path('games/<int:game_id>/', views.game_detail_view, name='game_detail'),
    path('favorites/add/<int:pk>/', views.add_favorite, name='add_favorite'),
    path('favorites/remove/<int:pk>/', views.remove_favorite, name='remove_favorite'),
    path('reservations/', views.game_reservations, name='game_reservations'),
    path('leaderboards/', views.leaderboards, name='leaderboards'),
    path('favoritegame/<int:game_id>', views.favorite_game_view, name='favorite_game'),
    path('gameform/', views.gameform, name='gameform'),
    path('reservation/', views.reservation_view, name='reservation'),
    path('reservationlist/', views.reservation_list_view, name='reservation_list'),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('achievement/<int:game_id>', views.achievement_view, name='achievement'),
    path('chat/<int:room_id>/', views.chat_room_view, name='chat_room'),
    path('chat/<int:room_id>/get_messages/', views.get_messages, name='get_messages'),
    path('chat/<int:room_id>/send_message/', views.send_message, name='send_message'),
    path('shoplocation/', views.shop_location_view, name='shop_location'),
    path('favoritegames/', views.favorite_games_list_view, name='favorite_games_list'),
    path('payments/<int:reservation_id>', views.payments_view, name='payments'),
    path('mpesa/<int:reservation_id>/', views.mpesa_view, name='mpesa'),
    path('paypal/<int:reservation_id>/', views.paypal_view, name='paypal'),
    path('paymentsuccess/', views.payment_success, name='payment_success'),
    path('stripe/<int:reservation_id>/', views.stripe_view, name='stripe'),
    path('create-checkout-session/<int:reservation_id>/', views.create_checkout_session, name='create_checkout_session'),
    path('reservation-success/', views.reservation_success, name='reservation_success'),
    path('reservation-cancel/', views.reservation_cancel, name='reservation_cancel'),
]