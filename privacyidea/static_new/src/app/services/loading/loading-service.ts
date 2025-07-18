import { HttpEvent } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, Subscription } from 'rxjs';

export interface LoadingServiceInterface {
  addListener(id: string, listener: (isLoading: boolean) => void): void;
  removeListener(id: string): void;
  notifyListeners(): void;
  addLoading(loading: {
    key: string;
    observable: Observable<HttpEvent<unknown>>;
    url: string;
  }): void;
  getLoadingUrls(): { key: string; url: string }[];
  clearAllLoadings(): void;
  isLoading(): boolean;
  removeLoading(key: string): void;
}

@Injectable({
  providedIn: 'root',
})
export class LoadingService implements LoadingServiceInterface {
  listeners: { [key: string]: (isLoading: boolean) => void } = {};
  loadings: { key: string; subscription: Subscription; url: string }[] = [];

  addListener(id: string, listener: (isLoading: boolean) => void): void {
    this.listeners[id] = listener;
  }

  removeListener(id: string): void {
    delete this.listeners[id];
  }

  notifyListeners(): void {
    Object.values(this.listeners).forEach((l) => l(this.isLoading()));
  }

  addLoading(loading: {
    key: string;
    observable: Observable<HttpEvent<unknown>>;
    url: string;
  }): void {
    const subscription = loading.observable.subscribe({
      complete: () => {
        this.removeLoading(loading.key);
      },
      error: (_) => {
        this.removeLoading(loading.key);
      },
    });
    this.loadings.push({ key: loading.key, subscription, url: loading.url });
    this.notifyListeners();
  }

  getLoadingUrls(): { key: string; url: string }[] {
    return this.loadings.map((l) => {
      return { key: l.key, url: l.url };
    });
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
