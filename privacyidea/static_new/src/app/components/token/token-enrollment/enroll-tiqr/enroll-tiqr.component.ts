import { Component, Input, signal, WritableSignal } from '@angular/core';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { TokenComponent } from '../../token.component';
import { SystemService } from '../../../../services/system/system.service';

@Component({
  selector: 'app-enroll-tiqr',
  imports: [MatFormField, MatInput, MatLabel, ReactiveFormsModule, FormsModule],
  templateUrl: './enroll-tiqr.component.html',
  styleUrl: './enroll-tiqr.component.scss',
})
export class EnrollTiqrComponent {
  text = TokenComponent.tokenTypeOptions.find((type) => type.key === 'tiqr')
    ?.text;
  @Input() description!: WritableSignal<string>;
  @Input() defaultTiQRIsSet = signal(false);

  constructor(private systemService: SystemService) {}

  ngOnInit(): void {
    this.systemService.getSystemConfig().subscribe((response) => {
      const config = response?.result?.value;
      if (
        config &&
        config['tiqr.infoUrl'] &&
        config['tiqr.logoUrl'] &&
        config['tiqr.regServer']
      ) {
        this.defaultTiQRIsSet.set(true);
      }
    });
  }
}
