import { Component, Input, WritableSignal } from '@angular/core';
import { TokenComponent } from '../../token.component';
import { FormsModule } from '@angular/forms';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';

@Component({
  selector: 'app-enroll-passkey',
  imports: [FormsModule, MatFormField, MatInput, MatLabel],
  templateUrl: './enroll-passkey.component.html',
  styleUrl: './enroll-passkey.component.scss',
})
export class EnrollPasskeyComponent {
  text = TokenComponent.tokenTypes.find((type) => type.key === 'passkey')?.text;
  @Input() description!: WritableSignal<string>;
}
