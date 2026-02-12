import { Component, input, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-questionnaire-config',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatExpansionModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule
  ],
  templateUrl: './questionnaire-config.component.html',
  styles: `
    :host {
      display: block;
    }
  `
})
export class QuestionnaireConfigComponent {
  formData = input.required<Record<string, any>>();
  questionKeys = input.required<string[]>();

  onAddQuestion = output<string>();
  onDeleteEntry = output<string>();

  newQuestionText = signal('');

  addQuestion() {
    if (this.newQuestionText()) {
      this.onAddQuestion.emit(this.newQuestionText());
      this.newQuestionText.set('');
    }
  }

  deleteEntry(key: string) {
    this.onDeleteEntry.emit(key);
  }
}
