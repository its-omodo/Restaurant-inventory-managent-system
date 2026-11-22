from django.db import models

class Employee(models.Model):
    employee_number = models.CharField(max_length=30, unique=True)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    position = models.CharField(max_length=100)
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="employees")
    section = models.ForeignKey("branches.Section", on_delete=models.PROTECT, related_name="employees")
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.employee_number} - {self.first_name} {self.last_name}"

class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendance")
    date = models.DateField()
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)

class Shift(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="shifts")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    section = models.ForeignKey("branches.Section", on_delete=models.PROTECT)
    station = models.CharField(max_length=100, blank=True)
