import { Component, Input, WritableSignal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { TokenComponent } from '../../token.component';
import { MatError } from '@angular/material/select';

@Component({
  selector: 'app-enroll-sshkey',
  imports: [FormsModule, MatFormField, MatInput, MatLabel, MatError],
  templateUrl: './enroll-sshkey.component.html',
  styleUrl: './enroll-sshkey.component.scss',
})
export class EnrollSshkeyComponent {
  text = TokenComponent.tokenTypeOptions.find((type) => type.key === 'sshkey')
    ?.text;
  @Input() description!: WritableSignal<string>;
  @Input() sshPublicKey!: WritableSignal<string>;
}
