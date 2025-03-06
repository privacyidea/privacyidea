import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class LoadingService {
  listeners: { [key: string]: (isLoading: boolean) => void } = {};
  addListener(id: string, listener: (isLoading: boolean) => void): void {
    this.listeners[id] = listener;
  }
  removeListener(id: string): void {
    delete this.listeners[id];
  }
  notifyListeners(): void {
    Object.values(this.listeners).forEach((l) => l(this.isLoading()));
  }

  loadings: { key: string; observable: Observable<any> }[] = [];
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

  private removeLoading(key: string): void {
    this.loadings = this.loadings.filter((l) => l.key !== key);
    this.notifyListeners();
  }

  clearAllLoadings(): void {
    this.loadings = [];
    this.notifyListeners();
  }

  isLoading(): boolean {
    return this.loadings.length > 0;
  }

  constructor() {}
}
