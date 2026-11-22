from django.contrib.auth.models import AbstractUser
from django.db import models

class Role(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    CEO = "CEO", "CEO"
    HR = "HR", "HR"
    FINANCE = "FINANCE", "Finance"
    PROCUREMENT = "PROCUREMENT", "Procurement"
    CALL_CENTER = "CALL_CENTER", "Call Center"
    AREA_COACH = "AREA_COACH", "Area Coach"
    RGM = "RGM", "RGM"
    CHICKEN_SUPERVISOR = "CHICKEN_SUPERVISOR", "Chicken Shift Supervisor"
    PIZZA_SUPERVISOR = "PIZZA_SUPERVISOR", "Pizza Shift Supervisor"

class User(AbstractUser):
    role = models.CharField(max_length=40, choices=Role.choices, default=Role.RGM)
    branches = models.ManyToManyField("branches.Branch", blank=True, related_name="users")
    sections = models.ManyToManyField("branches.Section", blank=True, related_name="users")

    def has_global_access(self):
        return self.role in {
            Role.ADMIN, Role.CEO, Role.HR, Role.FINANCE,
            Role.PROCUREMENT, Role.CALL_CENTER, Role.AREA_COACH,
        }

    def can_access_branch(self, branch):
        return self.has_global_access() or self.branches.filter(pk=branch.pk).exists()

    def can_access_section(self, section):
        if self.has_global_access():
            return True
        if self.role == Role.RGM:
            return self.branches.filter(pk=section.branch_id).exists()
        return self.sections.filter(pk=section.pk).exists()
