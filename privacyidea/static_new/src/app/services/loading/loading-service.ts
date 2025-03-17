import { Injectable } from '@angular/core';
import { Observable, Subscription } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class LoadingService {
  listeners: { [key: string]: (isLoading: boolean) => void } = {};
  loadings: { key: string; subscription: Subscription }[] = [];

  constructor() {}

  addListener(id: string, listener: (isLoading: boolean) => void): void {
    this.listeners[id] = listener;
  }

  removeListener(id: string): void {
    delete this.listeners[id];
  }

  notifyListeners(): void {
    Object.values(this.listeners).forEach((l) => l(this.isLoading()));
  }

  addLoading(loading: { key: string; observable: Observable<any> }): void {
    const subscription = loading.observable.subscribe({
      complete: () => {
        this.removeLoading(loading.key);
      },
      error: (_) => {
        this.removeLoading(loading.key);
      },
    });
    this.loadings.push({ key: loading.key, subscription });
    this.notifyListeners();
  }

  clearAllLoadings(): void {
    this.loadings.forEach((l) => {
      l.subscription.unsubscribe();
    });
    this.loadings = [];
    this.notifyListeners();
  }

  isLoading(): boolean {
    return this.loadings.length > 0;
  }

  removeLoading(key: string): void {
    this.loadings = this.loadings.filter((l) => l.key !== key);
    this.notifyListeners();
  }
}
