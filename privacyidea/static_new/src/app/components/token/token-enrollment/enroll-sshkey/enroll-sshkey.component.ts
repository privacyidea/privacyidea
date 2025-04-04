import { Component, Input, WritableSignal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatError } from '@angular/material/select';
import { TokenService } from '../../../../services/token/token.service';

@Component({
  selector: 'app-enroll-sshkey',
  imports: [FormsModule, MatFormField, MatInput, MatLabel, MatError],
  templateUrl: './enroll-sshkey.component.html',
  styleUrl: './enroll-sshkey.component.scss',
})
export class EnrollSshkeyComponent {
  text = this.tokenService
    .tokenTypeOptions()
    .find((type) => type.key === 'sshkey')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() sshPublicKey!: WritableSignal<string>;

  constructor(private tokenService: TokenService) {}
}
