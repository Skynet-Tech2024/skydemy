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
from .models import Activity

def log_activity(user, action, description, link=None, ip_address=None):
    """
    Log a user activity in the database.
    
    Args:
        user: User object (or None for system actions)
        action: string from Activity.ACTION_TYPES
        description: human-readable description
        link: optional URL to the related object
        ip_address: optional IP address
    """
    Activity.objects.create(
        user=user,
        action=action,
        description=description,
        link=link,
        ip_address=ip_address
    )