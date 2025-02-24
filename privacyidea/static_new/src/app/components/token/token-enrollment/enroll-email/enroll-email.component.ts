import { Component, Input, WritableSignal } from '@angular/core';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenComponent } from '../../token.component';

@Component({
  selector: 'app-enroll-email',
  imports: [
    MatCheckbox,
    MatFormField,
    MatInput,
    MatLabel,
    ReactiveFormsModule,
    FormsModule,
  ],
  templateUrl: './enroll-email.component.html',
  styleUrl: './enroll-email.component.scss',
})
export class EnrollEmailComponent {
  text = TokenComponent.tokenTypes.find((type) => type.key === 'email')?.text;
  @Input() description!: WritableSignal<string>;
  @Input() emailAddress!: WritableSignal<string>;
  @Input() readEmailDynamically!: WritableSignal<boolean>;
}
