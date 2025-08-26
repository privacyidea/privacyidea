import { Injectable } from "@angular/core";
import { MatSnackBar, MatSnackBarRef } from "@angular/material/snack-bar";
import { Subscription, timer } from "rxjs";

export interface NotificationServiceInterface {
  remainingTime: number;
  timerSub: Subscription;
  startTime: number;

  openSnackBar(message: string): void;
}

@Injectable({
  providedIn: "root"
})
export class NotificationService implements NotificationServiceInterface {
  private totalDuration: number = 5000;
  remainingTime: number = this.totalDuration;
  timerSub: Subscription = new Subscription();
  startTime: number = 0;

  constructor(readonly snackBar: MatSnackBar) {
  }

  openSnackBar(message: string): void {
    const snackBarRef = this.snackBar.open(message, "🗙", {
      horizontalPosition: "center",
      verticalPosition: "bottom",
      duration: undefined
    });

    this.remainingTime = this.totalDuration;
    this.startTime = Date.now();
    this.startTimer(snackBarRef);

    snackBarRef.afterOpened().subscribe(() => {
      const snackBarElement = (snackBarRef.containerInstance as any)._elementRef
        .nativeElement;
      snackBarElement.addEventListener("mouseenter", () => this.onMouseEnter());
      snackBarElement.addEventListener("mouseleave", () =>
        this.onMouseLeave(snackBarRef)
      );
    });
  }

  private startTimer<T>(snackBarRef: MatSnackBarRef<T>): void {
    this.clearTimer();
    this.timerSub = timer(this.remainingTime).subscribe(() => {
      snackBarRef.dismiss();
    });
  }

  private clearTimer(): void {
    if (this.timerSub) {
      this.timerSub.unsubscribe();
    }
  }

  private onMouseEnter(): void {
    this.clearTimer();
    const elapsed = Date.now() - this.startTime;
    this.remainingTime = Math.max(this.remainingTime - elapsed, 0);
  }

  private onMouseLeave<T>(snackBarRef: MatSnackBarRef<T>): void {
    if (this.remainingTime > 0) {
      this.startTime = Date.now();
      this.startTimer(snackBarRef);
    }
  }
}
