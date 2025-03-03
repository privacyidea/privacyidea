import { Component, effect, Input, WritableSignal } from '@angular/core';
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
  text = TokenComponent.tokenTypes.find((type) => type.key === 'sshkey')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() sshPublicKey!: WritableSignal<string>;

  constructor() {
    effect(() => {
      if (this.sshPublicKey()) {
        const parts = this.sshPublicKey().split(' ');
        if (parts.length >= 3) {
          this.description.set(parts[2]);
        } else {
          this.description.set('');
        }
      }
    });
  }
}
