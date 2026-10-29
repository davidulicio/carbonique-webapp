from rest_framework.exceptions import PermissionDenied
from inventory.models import Site

def role_for(user):
    if not user or not user.is_authenticated or not user.is_active:
        return None
    if user.is_superuser:
        return "admin"
    try:
        return user.team_member.role
    except Exception:
        return None

def display_name(user):
    return user.get_full_name() or user.email or user.username if user else "Imported record"

def require_role(user, *roles):
    if role_for(user) not in roles:
        raise PermissionDenied("Your team role does not allow this action.")

def network_admin(user):
    return role_for(user) == "admin" and (user.is_superuser or not user.team_member.sites.exists())


def require_network_admin(user):
    if not network_admin(user):
        raise PermissionDenied("Network-wide administrator access is required to manage accounts and shared checklists.")


def accessible_sites(user):
    role = role_for(user)
    if not role:
        return Site.objects.none()
    if user.is_superuser:
        return Site.objects.all()
    permitted = user.team_member.sites.all()
    return permitted if permitted.exists() else Site.objects.all()

def require_site(user, site_id, writable=False):
    try:
        site = accessible_sites(user).get(pk=site_id)
    except (Site.DoesNotExist, ValueError, TypeError):
        raise PermissionDenied("You do not have access to this site.")
    if writable and site.is_archived:
        raise PermissionDenied("This site is archived. An administrator can restore it first.")
    return site
