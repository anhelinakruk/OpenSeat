from django.db import models

# Create your models here.
class Station(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=5)

    def __str__(self):
        return self.name
    
class Train(models.Model):
    number = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.number} - {self.name}"
    
class Car(models.Model):
    train = models.ForeignKey(Train, on_delete=models.CASCADE)
    number = models.CharField(max_length=10)
    car_class = models.CharField(max_length=1)
    car_type = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.train.number} - Car {self.number} ({self.car_type})"
    
class Seat(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    number = models.CharField(max_length=10)
    seat_type = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.car.train.number} - Car {self.car.number} - Seat {self.number}"
    
class Route(models.Model):
    train = models.ForeignKey(Train, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.train.number} - {self.name}"