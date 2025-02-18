import { Component, Input, WritableSignal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { TokenComponent } from '../../token.component';

@Component({
  selector: 'app-enroll-sshkey',
  imports: [FormsModule, MatFormField, MatInput, MatLabel],
  templateUrl: './enroll-sshkey.component.html',
  styleUrl: './enroll-sshkey.component.scss',
})
export class EnrollSshkeyComponent {
  text = TokenComponent.tokenTypes.find((type) => type.key === 'sshkey')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() sshPublicKey!: WritableSignal<string>;
}
