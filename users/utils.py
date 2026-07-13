from .models import Notification

def create_notification(user, notification_type, title, message, link=None):
    """
    Create a notification for a user.
    
    Args:
        user: User object
        notification_type: One of Notification.NOTIFICATION_TYPES keys
        title: Short title of notification
        message: Detailed message
        link: Optional URL to redirect when notification is clicked
    """
    Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link
    )