import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root',
})
export class LoadingService {
  listeners: { [key: string]: () => void } = {};
  addListener(id: string, listener: () => void): void {
    console.log('Adding listener', id);
    this.listeners[id] = listener;
  }
  removeListener(id: string): void {
    console.log('Removing listener', id);
    delete this.listeners[id];
  }
  notifyListeners(): void {
    console.log('Notifying listeners');
    Object.values(this.listeners).forEach((l) => l());
  }

  loadings: string[] = [];
  addLoading(id: string): void {
    console.log('Adding loading', id);
    this.loadings.push(id);
    this.notifyListeners();
  }
  removeLoading(id: string): void {
    console.log('Removing loading', id);
    this.loadings = this.loadings.filter((l) => l !== id);
    this.notifyListeners();
  }
  clean(): void {
    console.log('Cleaning loadings');
    this.loadings = [];
    this.notifyListeners();
  }

  isLoading(): boolean {
    console.log('Checking if loading');
    return this.loadings.length > 0;
  }

  constructor() {}
}
