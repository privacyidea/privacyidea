import { Component, Input, WritableSignal } from '@angular/core';
import {
  MatError,
  MatFormField,
  MatHint,
  MatLabel,
} from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { MatOption } from '@angular/material/core';
import { MatSelect } from '@angular/material/select';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenComponent } from '../../token.component';

@Component({
  selector: 'app-enroll-daypassword',
  imports: [
    MatFormField,
    MatInput,
    MatLabel,
    MatOption,
    MatSelect,
    ReactiveFormsModule,
    FormsModule,
    MatHint,
    MatError,
  ],
  templateUrl: './enroll-daypassword.component.html',
  styleUrl: './enroll-daypassword.component.scss',
})
export class EnrollDaypasswordComponent {
  text = TokenComponent.tokenTypeOptions.find(
    (type) => type.key === 'daypassword',
  )?.text;
  @Input() description!: WritableSignal<string>;
  @Input() otpLength!: WritableSignal<number>;
  @Input() otpKey!: WritableSignal<string>;
  @Input() hashAlgorithm!: WritableSignal<string>;
  @Input() timeStep!: WritableSignal<number | string>;

  ngOnInit() {
    this.timeStep.set('');
  }
}
