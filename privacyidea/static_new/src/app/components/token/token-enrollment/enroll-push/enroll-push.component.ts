import { Component, Input, WritableSignal } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import {
  BasicEnrollmentOptions,
  TokenService,
} from '../../../../services/token/token.service';

export interface PushEnrollmentOptions extends BasicEnrollmentOptions {
  type: 'push';
  // generateOnServer is implicitly true (genkey: 1 in service)
  // For consistency, we can add it if it might be configurable in the future.
  generateOnServer?: boolean; // Defaulted to true by service if not provided
}
@Component({
  selector: 'app-enroll-push',
  imports: [ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-push.component.html',
  styleUrl: './enroll-push.component.scss',
})
export class EnrollPushComponent {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'spass')?.text;
  @Input() description!: WritableSignal<string>;

  constructor(private tokenService: TokenService) {}
}
