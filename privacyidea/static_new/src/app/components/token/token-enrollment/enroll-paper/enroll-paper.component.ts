import { Component, Input, WritableSignal } from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenComponent } from '../../token.component';

@Component({
  selector: 'app-enroll-paper',
  imports: [MatFormField, MatInput, MatLabel, ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-paper.component.html',
  styleUrl: './enroll-paper.component.scss',
})
export class EnrollPaperComponent {
  text = TokenComponent.tokenTypeOptions.find((type) => type.key === 'paper')
    ?.text;
  @Input() description!: WritableSignal<string>;
}
