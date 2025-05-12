import { Component, signal } from '@angular/core';
import { MatInput } from '@angular/material/input';
import { MatError, MatFormField, MatLabel } from '@angular/material/form-field';
import { FormsModule } from '@angular/forms';
import { ContentService } from '../../../services/content/content.service';
import { MatButton } from '@angular/material/button';
import { MatIcon } from '@angular/material/icon';
import { TokenService } from '../../../services/token/token.service';

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
  tokenSerial = this.tokenService.tokenSerial;
  selectedContent = this.contentService.selectedContent;
  selectedToken = signal('');
  setPinValue = signal('');
  repeatPinValue = signal('');

  constructor(
    private contentService: ContentService,
    protected tokenService: TokenService,
  ) {}

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
