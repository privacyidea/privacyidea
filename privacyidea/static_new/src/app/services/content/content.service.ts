import {
  effect,
  inject,
  Injectable,
  linkedSignal,
  signal,
  WritableSignal,
} from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter, map } from 'rxjs';
import { TokenSelectedContentKey } from '../../components/token/token.component';
import { AuthService } from '../auth/auth.service';
import { toSignal } from '@angular/core/rxjs-interop';

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

@Injectable({ providedIn: 'root' })
export class ContentService {
  router = inject(Router);
  private authService = inject(AuthService);
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

  constructor() {
    effect(() => this.updateFromUrl(this.router.url));

    this.router.events
      .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
      .subscribe((e) => this.updateFromUrl(e.urlAfterRedirects));
  }

  tokenSelected(serial: string) {
    if (
      this.selectedContent().includes('container') ||
      !this.routeUrl().includes('token')
    ) {
      this.isProgrammaticTabChange.set(true);
    }
    this.router.navigate(['/tokens', serial]);
    this.tokenSerial.set(serial);
  }

  containerSelected(containerSerial: string) {
    if (
      this.selectedContent().includes('token') ||
      !this.routeUrl().includes('token')
    ) {
      this.isProgrammaticTabChange.set(true);
    }
    this.router.navigate(['/tokens', 'containers', containerSerial]);
    this.containerSerial.set(containerSerial);
  }

  private updateFromUrl(url: string) {
    if (/^\/tokens\/containers\/?$/.test(url)) {
      this.selectedContent.set('container_overview');
      this.tokenSerial.set('');
      this.containerSerial.set('');
      return;
    }

    if (/^\/tokens\/containers\/create/.test(url)) {
      this.selectedContent.set('container_create');
      return;
    }

    const containerDetail = url.match(/^\/tokens\/containers\/([^/]+)$/);
    if (containerDetail) {
      this.selectedContent.set('container_details');
      this.containerSerial.set(containerDetail[1]);
      this.tokenSerial.set('');
      return;
    }

    if (/^\/tokens\/?$/.test(url)) {
      this.selectedContent.set(
        this.authService.role() === 'user'
          ? 'token_self-service_menu'
          : 'token_overview',
      );
      this.tokenSerial.set('');
      this.containerSerial.set('');
      return;
    }

    if (/^\/tokens\/enroll/.test(url)) {
      this.selectedContent.set('token_enrollment');
      return;
    }

    if (/^\/tokens\/challenges/.test(url)) {
      this.selectedContent.set('token_challenges');
      return;
    }

    if (/^\/tokens\/applications/.test(url)) {
      this.selectedContent.set('token_applications');
      return;
    }

    if (/^\/tokens\/get-serial/.test(url)) {
      this.selectedContent.set('token_get_serial');
      return;
    }

    const tokenDetail = url.match(/^\/tokens\/([^/]+)$/);
    if (tokenDetail) {
      this.selectedContent.set('token_details');
      this.tokenSerial.set(tokenDetail[1]);
      this.containerSerial.set('');
      return;
    }
  }
}
