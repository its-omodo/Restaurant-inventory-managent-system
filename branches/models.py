from django.db import models

class Branch(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    location = models.CharField(max_length=255, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

class Section(models.Model):
    class Type(models.TextChoices):
        CHICKEN = "CHICKEN", "Chicken"
        PIZZA = "PIZZA", "Pizza"

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="sections")
    name = models.CharField(max_length=30, choices=Type.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["branch", "name"], name="unique_section_per_branch")
        ]

    def __str__(self):
        return f"{self.branch.name} - {self.get_name_display()}"
