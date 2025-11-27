import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MachineresolverPanelNewComponent } from './machineresolver-panel-new.component';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { FormsModule } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

describe('MachineresolverPanelNewComponent', () => {
  let component: MachineresolverPanelNewComponent;
  let fixture: ComponentFixture<MachineresolverPanelNewComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ MachineresolverPanelNewComponent ],
      imports: [
        FormsModule,
        MatExpansionModule,
        MatFormFieldModule,
        MatInputModule,
        MatButtonModule,
        MatIconModule,
        MatSelectModule,
        NoopAnimationsModule
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MachineresolverPanelNewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
