import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButton } from '@angular/material/button';
import { MatError, MatFormField, MatLabel } from '@angular/material/form-field';
import { MatIcon } from '@angular/material/icon';
import { MatInput } from '@angular/material/input';
import {
  ContentService,
  ContentServiceInterface,
} from '../../../services/content/content.service';
import {
  TokenService,
  TokenServiceInterface,
} from '../../../services/token/token.service';

@Component({
  selector: 'app-assign-token-self-service',
  imports: [
    MatError,
    MatFormField,
    MatFormField,
    MatLabel,
    MatInput,
    FormsModule,
    MatButton,
    MatIcon,
  ],
  templateUrl: './assign-token-self-service.component.html',
  styleUrl: './assign-token-self-service.component.scss',
})
export class AssignTokenSelfServiceComponent {
  private readonly contentService: ContentServiceInterface =
    inject(ContentService);
  private readonly tokenService: TokenServiceInterface = inject(TokenService);

  tokenSerial = this.tokenService.tokenSerial;
  selectedContent = this.contentService.selectedContent;
  selectedToken = signal('');
  setPinValue = signal('');
  repeatPinValue = signal('');

  constructor() {}

  assignUserToToken() {
    this.tokenService
      .assignUser({
        tokenSerial: this.selectedToken(),
        username: '',
        realm: '',
        pin: this.setPinValue(),
      })
      .subscribe({
        next: () => {
          this.selectedContent.set('token_details');
          this.tokenSerial.set(this.selectedToken());
        },
      });
  }
}
