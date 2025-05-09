import { Injectable, linkedSignal, signal } from '@angular/core';
import { TokenSelectedContent } from '../../components/token/token.component';
import { AuthService } from '../auth/auth.service';

@Injectable({
  providedIn: 'root',
})
export class ContentService {
  isProgrammaticTabChange = signal(false);
  selectedContent = linkedSignal<string, TokenSelectedContent>({
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

  constructor(private authService: AuthService) {}

  tokenSelected(serial: string) {
    if (this.selectedContent().includes('container')) {
      this.isProgrammaticTabChange.set(true);
    }
    this.selectedContent.set('token_details');
    this.tokenSerial.set(serial);
  }

  containerSelected(containerSerial: string) {
    if (this.selectedContent().includes('token')) {
      this.isProgrammaticTabChange.set(true);
    }
    this.selectedContent.set('container_details');
    this.containerSerial.set(containerSerial);
  }
}
