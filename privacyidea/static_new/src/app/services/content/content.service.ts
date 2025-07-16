import {
  inject,
  Injectable,
  linkedSignal,
  signal,
  WritableSignal,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router } from '@angular/router';
import { filter, map } from 'rxjs';
import { TokenSelectedContentKey } from '../../components/token/token.component';
import { AuthService } from '../auth/auth.service';

export interface ContentServiceInterface {
  router: Router;
  routeUrl: () => string;
  isProgrammaticTabChange: WritableSignal<boolean>;
  selectedContent: WritableSignal<TokenSelectedContentKey>;
  tokenSerial: WritableSignal<string>;
  containerSerial: WritableSignal<string>;
  tokenSelected: (serial: string) => void;
  containerSelected: (containerSerial: string) => void;
}

@Injectable({
  providedIn: 'root',
})
export class ContentService implements ContentServiceInterface {
  readonly router = inject(Router);
  routeUrl = toSignal(
    this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd),
      map(() => this.router.url),
    ),
    { initialValue: this.router.url },
  );
  isProgrammaticTabChange = signal(false);
  selectedContent = linkedSignal<string, TokenSelectedContentKey>({
    source: this.authService.role,
    computation: (role) => {
      return role === 'user' ? 'token_self-service_menu' : 'token_overview';
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

  constructor(public authService: AuthService) {}

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
