import { inject, Injectable, linkedSignal, signal } from '@angular/core';
import { TokenSelectedContent } from '../../components/token/token.component';
import { AuthService } from '../auth/auth.service';
import { NavigationEnd, Router } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class ContentService {
  private router = inject(Router);
  routeUrl = toSignal(
    this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd),
      map(() => this.router.url),
    ),
    { initialValue: this.router.url },
  );
  isProgrammaticTabChange = signal(false);
  selectedContent = linkedSignal<{ role: string }, TokenSelectedContent>({
    source: () => ({
      role: this.authService.role(),
      routeUrl: this.isProgrammaticTabChange() ? null : this.routeUrl(),
    }),
    computation: (source: any) => {
      return source.role === 'user'
        ? 'token_self-service_menu'
        : 'token_overview';
    },
  });
  tokenSerial = linkedSignal({
    source: this.selectedContent,
    computation: () => '',
  });
  containerSerial = linkedSignal({
    source: this.selectedContent,
    computation: () => '',
  });

  constructor(private authService: AuthService) {}

  tokenSelected(serial: string) {
    if (
      this.selectedContent().includes('container') ||
      !this.routeUrl().includes('token')
    ) {
      this.isProgrammaticTabChange.set(true);
    }
    this.selectedContent.set('token_details');
    this.tokenSerial.set(serial);
  }

  containerSelected(containerSerial: string) {
    if (
      this.selectedContent().includes('token') ||
      !this.routeUrl().includes('token')
    ) {
      this.isProgrammaticTabChange.set(true);
    }
    this.selectedContent.set('container_details');
    this.containerSerial.set(containerSerial);
  }
}
