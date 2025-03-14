import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class LoadingService {
  listeners: { [key: string]: (isLoading: boolean) => void } = {};
  loadings: { key: string; observable: Observable<any> }[] = [];

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
    loading.observable.subscribe({
      complete: () => {
        this.removeLoading(loading.key);
      },
      error: (_) => {
        this.removeLoading(loading.key);
      },
    });
    this.loadings.push(loading);
    this.notifyListeners();
  }

  clearAllLoadings(): void {
    this.loadings.forEach((l) => l.observable.forEach((o) => o.unsubscribe()));
    this.loadings = [];
    this.notifyListeners();
  }

  isLoading(): boolean {
    return this.loadings.length > 0;
  }

  removeLoading(key: string): void {
    const loadingToRemove = this.loadings.find((l) => l.key === key);
    loadingToRemove?.observable.forEach((o) => o.unsubscribe());
    this.loadings = this.loadings.filter((l) => l.key !== key);
    this.notifyListeners();
  }
}
