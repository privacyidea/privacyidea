import { Component, Input, WritableSignal } from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenComponent } from '../../token.component';

@Component({
  selector: 'app-enroll-tiqr',
  imports: [MatFormField, MatInput, MatLabel, ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-tiqr.component.html',
  styleUrl: './enroll-tiqr.component.scss',
})
export class EnrollTiqrComponent {
  text = TokenComponent.tokenTypes.find((type) => type.key === 'tiqr')?.text;
  @Input() description!: WritableSignal<string>;
}
